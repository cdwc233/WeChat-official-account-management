import os
import uuid
from datetime import datetime

import markdown
from flask import Flask, render_template, request, jsonify, url_for, Response, stream_with_context

from config import config
from services.models import db, NormalizedArticle, SourceArticle, PublishArticle

app = Flask(__name__)

# 加载配置
app.config.from_object(config['development'])

# 配置上传
UPLOAD_FOLDER = 'static/images'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp', 'svg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 限制16MB

def allowed_file(filename):
    """检查文件扩展名是否允许"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

# 初始化数据库
db.init_app(app)

@app.route('/')
def index():
    # 查询最新N篇文章，按创建时间降序排列（只显示WUHU类型，排除已舍弃的文章）
    articles = NormalizedArticle.query.filter_by(source_type='WUHU').filter(NormalizedArticle.process_status != 4).order_by(NormalizedArticle.created_at.desc()).limit(app.config['ARTICLES_PER_PAGE']).all()
    return render_template('index.html', articles=articles)

@app.route('/article/<int:article_id>')
def article_detail(article_id):
    """文章详情页(normalized_articles表,nid为主键)"""
    article = NormalizedArticle.query.get_or_404(article_id)
    
    # 将 Markdown 内容转换为 HTML
    if article.content:
        # 使用 markdown 库，启用额外的扩展功能
        html_content = markdown.markdown(
            article.content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code', 'nl2br']
        )
        
        # 修复图片路径：如果 src 以 static/ 开头但没有 /，则补全 /
        import re
        html_content = re.sub(
            r'<img ([^>]*?)src="(static/[^"]+)"',
            r'<img \1src="/\2"',
            html_content
        )
    else:
        html_content = '<p class="text-gray-500">暂无内容</p>'
    
    # 传递文章类型和返回路径
    return render_template('article_detail.html', 
                         article=article, 
                         html_content=html_content,
                         article_type='article',
                         back_url='/')

@app.route('/crawler')
def crawler_index():
    """爬虫文章列表页(只显示TEJIAN类型，排除已舍弃的文章)"""
    # 查询所有爬虫文章，按创建时间降序排列，排除 process_status=4 的文章
    articles = NormalizedArticle.query.filter_by(source_type='TEJIAN').filter(NormalizedArticle.process_status != 4).order_by(NormalizedArticle.created_at.desc()).all()
    return render_template('crawler_index.html', articles=articles)

@app.route('/raw-article/<int:article_id>')
def raw_article_detail(article_id):
    """爬虫文章详情页(normalized_articles表,nid为主键)"""
    article = NormalizedArticle.query.get_or_404(article_id)
    
    # 将 Markdown 内容转换为 HTML
    if article.content:
        # 使用 markdown 库，启用额外的扩展功能
        html_content = markdown.markdown(
            article.content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code', 'nl2br']
        )
        
        # 修复图片路径：如果 src 以 static/ 开头但没有 /，则补全 /
        import re
        html_content = re.sub(
            r'<img ([^>]*?)src="(static/[^"]+)"',
            r'<img \1src="/\2"',
            html_content
        )
    else:
        html_content = '<p class="text-gray-500">暂无内容</p>'
    
    # 复用同一个模板，传递文章类型和返回路径
    return render_template('article_detail.html', 
                         article=article, 
                         html_content=html_content,
                         article_type='raw-article',
                         back_url='/crawler')

@app.route('/publish')
def publish_index():
    """发布文章列表页(publish_articles表)"""
    # 查询所有发布文章，按创建时间降序排列
    articles = PublishArticle.query.order_by(PublishArticle.created_at.desc()).all()
    return render_template('publish_index.html', articles=articles)

@app.route('/publish-article/<int:article_id>')
def publish_article_detail(article_id):
    """发布文章详情页(publish_articles表,pid为主键)"""
    article = PublishArticle.query.get_or_404(article_id)
    
    # 使用已转换的HTML内容
    content_html = article.content_html if article.content_html else '<p class="text-gray-500">暂无内容</p>'
    
    return render_template('publish_article_detail.html', 
                         article=article, 
                         content_html=content_html)

@app.route('/api/crawl', methods=['POST'])
def crawl_articles():
    """API接口: 手动触发爬取"""
    try:
        from services.crawler import CaseiCrawler
        
        # 创建爬虫实例
        crawler = CaseiCrawler(app=app)
        
        # 爬取所有文章
        stats = crawler.crawl_and_save_all(delay=1, skip_existing=True)
        
        return jsonify({
            'status': 'success',
            'message': f'爬取完成，成功 {stats["success"]} 篇，跳过 {stats["skipped"]} 篇，失败 {stats["failed"]} 篇',
            'total': stats['total'],
            'success': stats['success'],
            'skipped': stats['skipped'],
            'failed': stats['failed']
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/article/<int:article_id>', methods=['PUT'])
def update_article(article_id):
    """更新文章(normalized_articles表)"""
    try:
        article = NormalizedArticle.query.get_or_404(article_id)
        data = request.get_json()
        
        # 验证数据
        if not data.get('title'):
            return jsonify({
                'status': 'error',
                'message': '标题不能为空'
            }), 400
        
        if not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': '内容不能为空'
            }), 400
        
        # 更新文章
        article.title = data['title']
        article.content = data['content']
        article.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '文章更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/raw-article/<int:article_id>', methods=['PUT'])
def update_raw_article(article_id):
    """更新爬虫文章(normalized_articles表)"""
    try:
        article = NormalizedArticle.query.get_or_404(article_id)
        data = request.get_json()
        
        # 验证数据
        if not data.get('title'):
            return jsonify({
                'status': 'error',
                'message': '标题不能为空'
            }), 400
        
        if not data.get('content'):
            return jsonify({
                'status': 'error',
                'message': '内容不能为空'
            }), 400
        
        # 更新文章
        article.title = data['title']
        article.content = data['content']
        article.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '爬虫文章更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/upload-image/<int:article_id>', methods=['POST'])
def upload_image(article_id):
    """上传图片到文章对应的images文件夹(normalized_articles表)"""
    try:
        # 检查文章是否存在
        article = NormalizedArticle.query.get_or_404(article_id)
        
        # 检查是否有文件
        if 'image' not in request.files:
            return jsonify({
                'status': 'error',
                'message': '没有选择文件'
            }), 400
        
        file = request.files['image']
        
        # 检查文件名
        if file.filename == '':
            return jsonify({
                'status': 'error',
                'message': '没有选择文件'
            }), 400
        
        # 检查文件类型
        if not allowed_file(file.filename):
            return jsonify({
                'status': 'error',
                'message': f'不支持的文件格式，仅支持: {", ".join(ALLOWED_EXTENSIONS)}'
            }), 400
        
        # 获取文件扩展名
        ext = file.filename.rsplit('.', 1)[1].lower()
        
        # 从文章链接中提取文件夹名（/s/ 后面的部分）
        folder_name = None
        if article.source_url:
            # 示例: https://mp.weixin.qq.com/s/SHgnw6-sgzUoB_AaV8OflQ
            # 提取 SHgnw6-sgzUoB_AaV8OflQ
            parts = article.source_url.split('/s/')
            if len(parts) > 1:
                # 去除可能的查询参数
                folder_name = parts[1].split('?')[0].split('#')[0]
        
        # 如果无法从链接提取，使用默认命名
        if not folder_name:
            folder_name = f"article_{article_id}"
        
        # 创建文章专属的图片文件夹
        article_image_folder = os.path.join(app.config['UPLOAD_FOLDER'], folder_name)
        os.makedirs(article_image_folder, exist_ok=True)
        
        # 生成唯一文件名（使用UUID避免重复）
        unique_filename = f"{uuid.uuid4().hex}.{ext}"
        filepath = os.path.join(article_image_folder, unique_filename)
        
        # 保存文件
        file.save(filepath)
        
        # 生成URL（使用相对路径）
        image_url = url_for('static', filename=f'images/{folder_name}/{unique_filename}')
        
        return jsonify({
            'status': 'success',
            'message': '图片上传成功',
            'url': image_url,
            'filename': unique_filename,
            'folder': folder_name
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'上传失败: {str(e)}'
        }), 500

@app.route('/api/markdown-to-html', methods=['POST'])
def markdown_to_html():
    """将 Markdown 转换为 HTML"""
    try:
        data = request.get_json()
        markdown_content = data.get('markdown', '')
        
        if not markdown_content:
            return jsonify({
                'status': 'error',
                'message': 'Markdown 内容为空'
            }), 400
        
        # 使用 markdown 库转换
        html_content = markdown.markdown(
            markdown_content,
            extensions=['extra', 'codehilite', 'tables', 'fenced_code', 'nl2br']
        )
        
        return jsonify({
            'status': 'success',
            'html': html_content
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

# 数据库测试接口
@app.route('/api/test-db')
def test_db():
    """测试数据库连接"""
    try:
        # 尝试查询文章数量
        normalized_count = NormalizedArticle.query.count()
        source_count = SourceArticle.query.count()
        wuhu_count = NormalizedArticle.query.filter_by(source_type='WUHU').count()
        tejian_count = NormalizedArticle.query.filter_by(source_type='TEJIAN').count()
        return jsonify({
            'status': 'success',
            'message': '数据库连接成功！',
            'normalized_article_count': normalized_count,
            'source_article_count': source_count,
            'wuhu_count': wuhu_count,
            'tejian_count': tejian_count
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'数据库连接失败: {str(e)}'
        }), 500

@app.route('/api/articles')
def get_articles():
    """获取最新N篇文章(WUHU类型，排除已舍弃的文章)"""
    try:
        articles = NormalizedArticle.query.filter_by(source_type='WUHU').filter(NormalizedArticle.process_status != 4).order_by(NormalizedArticle.created_at.desc()).limit(app.config['ARTICLES_PER_PAGE']).all()
        return jsonify({
            'status': 'success',
            'data': [article.to_dict() for article in articles]
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/check-cookie', methods=['GET'])
def check_cookie():
    """检测Cookie是否有效"""
    try:
        from services.sync_wechat_articles import check_cookie_valid
        
        # 检查是否需要自动刷新
        auto_refresh = request.args.get('auto_refresh', 'false').lower() == 'true'
        
        is_valid, message = check_cookie_valid(auto_refresh=auto_refresh)
        
        return jsonify({
            'status': 'success' if is_valid else 'error',
            'is_valid': is_valid,
            'message': message
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'is_valid': False,
            'message': f'检测失败: {str(e)}'
        }), 500

@app.route('/api/refresh-cookie', methods=['POST'])
def refresh_cookie():
    """手动触发Cookie刷新（用户确认后调用）"""
    try:
        from services.sync_wechat_articles import do_cookie_refresh
        
        is_valid, message = do_cookie_refresh()
        
        if is_valid:
            return jsonify({
                'status': 'success',
                'message': message
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'Cookie刷新失败: {str(e)}'
        }), 500

@app.route('/api/refresh-cookie-headless', methods=['POST'])
def refresh_cookie_headless():
    """无头模式刷新Cookie（启动后台浏览器并返回二维码）"""
    try:
        from services.cookie_picker import wait_for_login_and_capture, update_config_file
        import threading
        
        # 全局变量存储状态
        global _cookie_refresh_status
        _cookie_refresh_status = {
            'status': 'pending',  # pending, qr_ready, success, error
            'message': '正在启动浏览器...',
            'qr_path': None
        }
        
        def refresh_task():
            """后台任务：启动浏览器并等待登录"""
            try:
                def qr_callback(qr_path):
                    """二维码生成后的回调"""
                    _cookie_refresh_status['status'] = 'qr_ready'
                    _cookie_refresh_status['message'] = '二维码已生成，请扫码登录'
                    _cookie_refresh_status['qr_path'] = qr_path
                    print(f"[Cookie刷新] 二维码已生成: {qr_path}")
                
                # 调用无头模式的cookie获取
                new_config = wait_for_login_and_capture(
                    browser='edge',
                    headless=True,
                    qr_callback=qr_callback
                )
                
                if new_config:
                    # 更新配置文件
                    success = update_config_file(new_config)
                    if success:
                        # 重新加载 sync_wechat_articles 模块的配置
                        print("[Cookie刷新] 重新加载同步模块配置...")
                        from services.sync_wechat_articles import reload_wechat_config
                        reload_wechat_config()
                        
                        _cookie_refresh_status['status'] = 'success'
                        _cookie_refresh_status['message'] = 'Cookie刷新成功！'
                        print("[Cookie刷新] 刷新成功")
                    else:
                        _cookie_refresh_status['status'] = 'error'
                        _cookie_refresh_status['message'] = '配置文件更新失败'
                        print("[Cookie刷新] 配置文件更新失败")
                else:
                    _cookie_refresh_status['status'] = 'error'
                    _cookie_refresh_status['message'] = 'Cookie获取失败'
                    print("[Cookie刷新] Cookie获取失败")
                    
            except Exception as e:
                _cookie_refresh_status['status'] = 'error'
                _cookie_refresh_status['message'] = f'刷新失败: {str(e)}'
                print(f"[Cookie刷新] 异常: {str(e)}")
                import traceback
                traceback.print_exc()
        
        # 启动后台线程
        thread = threading.Thread(target=refresh_task, daemon=True)
        thread.start()
        
        return jsonify({
            'status': 'success',
            'message': '已启动Cookie刷新任务，请等待二维码生成'
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'启动失败: {str(e)}'
        }), 500

@app.route('/api/refresh-cookie-status', methods=['GET'])
def refresh_cookie_status():
    """查询Cookie刷新状态"""
    try:
        global _cookie_refresh_status
        
        # 如果还没有初始化状态
        if '_cookie_refresh_status' not in globals():
            return jsonify({
                'status': 'idle',
                'message': '未启动刷新任务'
            })
        
        response = {
            'status': _cookie_refresh_status['status'],
            'message': _cookie_refresh_status['message']
        }
        
        # 如果二维码已就绪，返回二维码的URL
        if _cookie_refresh_status['status'] == 'qr_ready' and _cookie_refresh_status['qr_path']:
            # 转换为URL路径
            qr_path = _cookie_refresh_status['qr_path']
            # 提取 static/ 后面的部分
            if 'static' in qr_path:
                relative_path = qr_path.split('static' + os.sep)[1].replace('\\', '/')
                response['qr_url'] = url_for('static', filename=relative_path)
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'查询失败: {str(e)}'
        }), 500

@app.route('/api/sync', methods=['POST'])
def sync_articles():
    """同步微信文章"""
    try:
        # 导入同步函数
        from services.sync_wechat_articles import sync_wechat_articles, check_cookie_valid
        from services.clean import clean_old_articles
        
        # 先检测Cookie是否有效
        is_valid, message = check_cookie_valid()
        if not is_valid:
            return jsonify({
                'status': 'error',
                'message': f'Cookie检测失败: {message}'
            }), 400
        
        # 执行同步（使用配置的文章数量）
        articles_count = app.config['ARTICLES_PER_PAGE']
        success_count = sync_wechat_articles(count=articles_count, skip_existing=False, target_success=articles_count)
        
        # 同步完成后自动清理旧文章
        print("[同步] 开始自动清理旧文章...")
        clean_result = clean_old_articles(articles_per_page=articles_count)
        
        return jsonify({
            'status': 'success',
            'message': f'同步完成，成功采集 {success_count} 篇文章',
            'count': success_count,
            'clean_result': clean_result
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/last-update-time')
def get_last_update_time():
    """获取最后更新时间（第N篇文章的更新时间,WUHU类型，排除已舍弃的文章）"""
    try:
        # 按更新时间降序排列，获取第N篇文章，排除已舍弃的
        articles = NormalizedArticle.query.filter_by(source_type='WUHU').filter(NormalizedArticle.process_status != 4).order_by(NormalizedArticle.updated_at.desc()).limit(app.config['ARTICLES_PER_PAGE']).all()
        
        if len(articles) >= app.config['ARTICLES_PER_PAGE']:
            last_update = articles[app.config['ARTICLES_PER_PAGE'] - 1].updated_at  # 第N篇（索引N-1）
        elif articles:
            last_update = articles[-1].updated_at  # 如果不足N篇，取最后一篇
        else:
            last_update = None
        
        return jsonify({
            'status': 'success',
            'last_update': last_update.strftime('%Y-%m-%d %H:%M:%S') if last_update else None
        })
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/clean', methods=['POST'])
def clean_old_articles_api():
    """清理旧文章，只保留最新的 ARTICLES_PER_PAGE 篇文章"""
    try:
        # 导入清理函数
        from services.clean import clean_old_articles
        
        # 执行清理（使用配置的文章数量）
        result = clean_old_articles(articles_per_page=app.config['ARTICLES_PER_PAGE'])
        
        return jsonify(result)
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/<article_type>/<int:article_id>/generate-summary', methods=['POST'])
def generate_summary(article_type, article_id):
    """生成文章摘要(normalized_articles表)"""
    try:
        # 导入AI处理函数
        from services.ai_process import generate_article_summary
        
        # 根据类型获取文章(都从normalized_articles表获取)
        if article_type in ['article', 'raw-article']:
            article = NormalizedArticle.query.get_or_404(article_id)
        else:
            return jsonify({
                'status': 'error',
                'message': '无效的文章类型'
            }), 400
        
        # 检查文章内容
        if not article.content:
            return jsonify({
                'status': 'error',
                'message': '文章内容为空，无法生成摘要'
            }), 400
        
        # 生成摘要
        success, message, summary = generate_article_summary(article.content)
        
        if success:
            return jsonify({
                'status': 'success',
                'message': message,
                'summary': summary
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
    except Exception as e:
        return jsonify({
            'status': 'error',
            'message': f'生成摘要失败: {str(e)}'
        }), 500

@app.route('/api/<article_type>/<int:article_id>/generate-cover', methods=['POST'])
def generate_cover(article_type, article_id):
    """生成文章封面，直接保存到固定路径 ai_images/{id}/cover.jpg (normalized_articles表)"""
    try:
        # 导入AI处理函数
        from services.ai_process import generate_cover_image
        
        # 根据类型获取文章(都从normalized_articles表获取)
        if article_type in ['article', 'raw-article']:
            article = NormalizedArticle.query.get_or_404(article_id)
        else:
            return jsonify({
                'status': 'error',
                'message': '无效的文章类型'
            }), 400
        
        # 检查文章标题
        if not article.title:
            return jsonify({
                'status': 'error',
                'message': '文章标题为空，无法生成封面'
            }), 400
        
        # 创建固定的保存路径: static/ai_images/{article_id}/cover.jpg
        cover_folder = os.path.join('static', 'ai_images', str(article_id))
        os.makedirs(cover_folder, exist_ok=True)
        
        # 固定文件名
        cover_filename = 'cover.jpg'
        save_path = os.path.join(cover_folder, cover_filename)
        
        print(f"[封面生成] 保存路径: {save_path}")
        
        # 生成封面（如果文件已存在会被覆盖）
        success, message, path = generate_cover_image(article.title, save_path)
        
        if success:
            # 生成URL和相对路径
            cover_relative_path = f'ai_images/{article_id}/{cover_filename}'
            cover_url = url_for('static', filename=cover_relative_path)
            
            print(f"[封面生成] 成功生成封面: {cover_url}")
            
            return jsonify({
                'status': 'success',
                'message': message,
                'cover_url': cover_url,
                'cover_path': cover_relative_path
            })
        else:
            return jsonify({
                'status': 'error',
                'message': message
            }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'生成封面失败: {str(e)}'
        }), 500

@app.route('/api/<article_type>/<int:article_id>/publish-ai-content', methods=['POST'])
def publish_ai_content(article_type, article_id):
    """发布AI生成的内容到publish_articles表"""
    try:
        data = request.get_json()
        
        # 获取所有数据
        title = data.get('title')
        content = data.get('content')
        cover_url = data.get('cover')  # 前端传来的相对URL
        summary = data.get('summary')
        target_platform = data.get('target_platform', 'WEIXIN')  # 默认微信平台
        
        # 验证必填字段
        if not title:
            return jsonify({
                'status': 'error',
                'message': '标题不能为空'
            }), 400
        
        if not content:
            return jsonify({
                'status': 'error',
                'message': '内容不能为空'
            }), 400
        
        if not summary:
            return jsonify({
                'status': 'error',
                'message': '摘要不能为空'
            }), 400
        
        # 获取normalized文章
        normalized_article = NormalizedArticle.query.get_or_404(article_id)
        
        # 处理封面路径：转换为绝对路径
        absolute_cover_path = None
        if cover_url:
            # cover_url 格式: /static/ai_images/{id}/cover.jpg
            # 转换为绝对路径
            if cover_url.startswith('/static/'):
                relative_path = cover_url.replace('/static/', '')
                # 拼接绝对路径
                absolute_cover_path = os.path.abspath(os.path.join('static', relative_path))
            else:
                absolute_cover_path = os.path.abspath(cover_url)
        
        # 拼接内容：摘要在前，content在后，中间换行
        combined_markdown = f"{summary}\n\n{content}"
        
        # 使用 mdtowechat.py 转换成HTML
        from services.mdtowechat import markdown_to_wechat
        content_html = markdown_to_wechat(combined_markdown)
        
        # 检查是否已存在该文章的发布记录
        existing_publish = PublishArticle.query.filter_by(
            nid=normalized_article.nid,
            target_platform=target_platform
        ).first()
        
        if existing_publish:
            # 更新已有记录
            existing_publish.title = title
            existing_publish.content_html = content_html
            existing_publish.cover_url = absolute_cover_path
            existing_publish.source_url = normalized_article.source_url
            existing_publish.updated_at = datetime.now()
            
            db.session.commit()
            
            print(f"[发布] 更新成功 - PID: {existing_publish.pid}, NID: {normalized_article.nid}, 封面: {absolute_cover_path}")
            
            return jsonify({
                'status': 'success',
                'message': 'AI内容发布成功！已更新到发布表',
                'pid': existing_publish.pid,
                'nid': normalized_article.nid,
                'title': title,
                'cover_absolute_path': absolute_cover_path,
                'content_html_length': len(content_html),
                'target_platform': target_platform,
                'action': 'update'
            })
        else:
            # 创建新的发布记录
            new_publish = PublishArticle(
                nid=normalized_article.nid,
                title=title,
                content_html=content_html,
                cover_url=absolute_cover_path,
                source_url=normalized_article.source_url,
                target_platform=target_platform,
                publish_status=0  # 待发布
            )
            
            db.session.add(new_publish)
            db.session.commit()
            
            print(f"[发布] 创建成功 - PID: {new_publish.pid}, NID: {normalized_article.nid}, 封面: {absolute_cover_path}")
            
            return jsonify({
                'status': 'success',
                'message': 'AI内容发布成功！已保存到发布表',
                'pid': new_publish.pid,
                'nid': normalized_article.nid,
                'title': title,
                'cover_absolute_path': absolute_cover_path,
                'content_html_length': len(content_html),
                'target_platform': target_platform,
                'action': 'create'
            })
            
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'发布失败: {str(e)}'
        }), 500

@app.route('/api/publish-article/<int:pid>', methods=['PUT'])
def update_publish_article(pid):
    """更新发布文章(publish_articles表)"""
    try:
        article = PublishArticle.query.get_or_404(pid)
        data = request.get_json()
        
        # 验证数据
        if not data.get('title'):
            return jsonify({
                'status': 'error',
                'message': '标题不能为空'
            }), 400
        
        if not data.get('content_html'):
            return jsonify({
                'status': 'error',
                'message': '内容不能为空'
            }), 400
        
        # 更新文章
        article.title = data['title']
        article.content_html = data['content_html']
        article.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '发布文章更新成功'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': str(e)
        }), 500

@app.route('/api/publish-to-wechat/<int:pid>', methods=['POST'])
def publish_to_wechat_api(pid):
    """发布文章到微信公众号草稿箱"""
    try:
        from services.publish import publish_to_wechat
        
        # 调用发布方法
        result = publish_to_wechat(pid)
        
        if result['success']:
            return jsonify(result)
        else:
            return jsonify(result), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'发布接口异常: {str(e)}'
        }), 500

@app.route('/api/publish-to-website/<int:pid>', methods=['POST'])
def publish_to_website_api(pid):
    """发布文章到远程网站数据库"""
    try:
        import pymysql
        from pymysql.cursors import DictCursor
        
        # 获取本地文章
        article = PublishArticle.query.get_or_404(pid)
        
        # 验证是否为 TEJIAN 类型
        if article.target_platform != 'TEJIAN':
            return jsonify({
                'success': False,
                'message': '只能发布特检类型的文章到网站'
            }), 400
        
        # 连接远程数据库
        connection = pymysql.connect(
            host=app.config['REMOTE_DB_HOST'],
            port=int(app.config['REMOTE_DB_PORT']),
            user=app.config['REMOTE_DB_USER'],
            password=app.config['REMOTE_DB_PASSWORD'],
            database=app.config['REMOTE_DB_NAME'],
            charset='utf8mb4',
            cursorclass=DictCursor
        )
        
        try:
            with connection.cursor() as cursor:
                # 检查是否已经发布过（根据 nid 查询）
                check_sql = "SELECT wid FROM website_articles WHERE nid = %s"
                cursor.execute(check_sql, (article.nid,))
                existing = cursor.fetchone()
                
                if existing:
                    return jsonify({
                        'success': False,
                        'message': '该文章已经发布到网站'
                    }), 400
                
                # 插入到远程数据库
                insert_sql = """
                    INSERT INTO website_articles 
                    (nid, title, content, cover_url, source_url, target_platform, publish_status, platform_article_id, created_at, updated_at)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """
                cursor.execute(insert_sql, (
                    article.nid,
                    article.title,
                    article.content_html,
                    article.cover_url,
                    article.source_url,
                    article.target_platform,
                    article.publish_status,
                    article.platform_article_id,
                    article.created_at,
                    article.updated_at
                ))
                
                connection.commit()
                wid = cursor.lastrowid
                
            # 更新本地文章的发布状态
            article.publish_status = 1  # 设置为已发布
            article.platform_article_id = f'website_{wid}'  # 记录远程 wid
            article.updated_at = datetime.now()
            db.session.commit()
                
            return jsonify({
                'success': True,
                'message': '文章已成功发布到网站',
                'wid': wid
            })
        finally:
            connection.close()
            
    except pymysql.Error as e:
        return jsonify({
            'success': False,
            'message': f'数据库错误: {str(e)}'
        }), 500
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'success': False,
            'message': f'发布失败: {str(e)}'
        }), 500

@app.route('/api/raw-article/<int:article_id>/discard', methods=['POST'])
def discard_raw_article(article_id):
    """舍弃爬虫文章(将 process_status 设置为 4)"""
    try:
        article = NormalizedArticle.query.get_or_404(article_id)
        
        # 检查是否为爬虫文章(TEJIAN类型)
        if article.source_type != 'TEJIAN':
            return jsonify({
                'status': 'error',
                'message': '只能舍弃爬虫文章'
            }), 400
        
        # 设置 process_status 为 4（已舍弃）
        article.process_status = 4
        article.updated_at = datetime.now()
        
        # 同时更新对应的 source_articles 表
        if article.source:
            article.source.process_status = 4
            article.source.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '文章已舍弃'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'舍弃失败: {str(e)}'
        }), 500

@app.route('/api/article/<int:article_id>/discard', methods=['POST'])
def discard_article(article_id):
    """舍弃首页文章(将 process_status 设置为 4)"""
    try:
        article = NormalizedArticle.query.get_or_404(article_id)
        
        # 检查是否为首页文章(WUHU类型)
        if article.source_type != 'WUHU':
            return jsonify({
                'status': 'error',
                'message': '只能舍弃首页文章'
            }), 400
        
        # 设置 process_status 为 4（已舍弃）
        article.process_status = 4
        article.updated_at = datetime.now()
        
        # 同时更新对应的 source_articles 表
        if article.source:
            article.source.process_status = 4
            article.source.updated_at = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'status': 'success',
            'message': '文章已舍弃'
        })
    except Exception as e:
        db.session.rollback()
        return jsonify({
            'status': 'error',
            'message': f'舍弃失败: {str(e)}'
        }), 500

@app.route('/api/article/<int:article_id>/publish-to-website', methods=['POST'])
def publish_to_website(article_id):
    """发布文章到微信(经过mdtowechat处理后保存到publish_articles表)"""
    try:
        # 获取normalized文章
        article = NormalizedArticle.query.get_or_404(article_id)
        
        # 检查文章内容
        if not article.content:
            return jsonify({
                'status': 'error',
                'message': '文章内容为空，无法发布'
            }), 400
        
        # 使用 mdtowechat 转换 Markdown 为微信HTML
        print(f"[微信发布] 开始转换文章: {article.title}")
        from services.mdtowechat import markdown_to_wechat
        content_html = markdown_to_wechat(article.content)
        print(f"[微信发布] HTML转换完成，长度: {len(content_html)} 字符")
        
        # 处理封面路径：转换为绝对路径
        absolute_cover_path = None
        if article.cover_url:
            # 如果是相对路径（以/开头或不以http开头），转换为绝对路径
            if article.cover_url.startswith('/static/'):
                relative_path = article.cover_url.replace('/static/', '')
                absolute_cover_path = os.path.abspath(os.path.join('static', relative_path))
            elif not article.cover_url.startswith('http'):
                # 其他相对路径
                absolute_cover_path = os.path.abspath(article.cover_url)
            else:
                # 已经是URL，保持不变
                absolute_cover_path = article.cover_url
        
        # 检查是否已存在该文章的发布记录（特检类型）
        existing_publish = PublishArticle.query.filter_by(
            nid=article.nid,
            target_platform='TEJIAN'
        ).first()
        
        if existing_publish:
            # 更新已有记录
            existing_publish.title = article.title
            existing_publish.content_html = content_html
            existing_publish.cover_url = absolute_cover_path
            existing_publish.source_url = article.source_url
            existing_publish.updated_at = datetime.now()
            
            db.session.commit()
            
            print(f"[特检发布] 更新成功 - PID: {existing_publish.pid}, NID: {article.nid}")
            
            return jsonify({
                'status': 'success',
                'message': '文章已更新到特检发布表！',
                'pid': existing_publish.pid,
                'nid': article.nid,
                'action': 'update'
            })
        else:
            # 创建新的发布记录
            new_publish = PublishArticle(
                nid=article.nid,
                title=article.title,
                content_html=content_html,
                cover_url=absolute_cover_path,
                source_url=article.source_url,
                target_platform='TEJIAN',  # 标记为特检类型
                publish_status=0  # 待发布
            )
            
            db.session.add(new_publish)
            db.session.commit()
            
            print(f"[特检发布] 创建成功 - PID: {new_publish.pid}, NID: {article.nid}")
            
            return jsonify({
                'status': 'success',
                'message': '文章已发布到特检发布表！',
                'pid': new_publish.pid,
                'nid': article.nid,
                'action': 'create'
            })
            
    except Exception as e:
        db.session.rollback()
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'发布失败: {str(e)}'
        }), 500

@app.route('/api/ai-chat', methods=['POST'])
def ai_chat():
    """AI对话接口，支持流式输出"""
    try:
        from openai import OpenAI
        import json
        
        data = request.get_json()
        messages = data.get('messages', [])
        article_content = data.get('article_content', '')
        
        if not messages:
            return jsonify({
                'status': 'error',
                'message': '消息不能为空'
            }), 400
        
        # 初始化OpenAI客户端
        client = OpenAI(
            base_url='https://api-inference.modelscope.cn/v1',
            api_key='ms-3069d74f-5376-49c8-83f5-bc59ac46a9a4',
        )
        
        # 构建系统提示词
        system_prompt = f"""你是一位专业的文章润色助手。你的任务是帮助用户改进文章内容。

当前文章内容：
{article_content[:2000] if article_content else '(未提供文章内容)'}

你可以：
1. 润色和改写用户提供的段落
2. 提供写作建议
3. 改进文章标题
4. 优化文章结构
5. 纠正语法和表达问题

请用简洁、专业的语言回答用户的问题。"""
        
        # 构建完整的消息列表
        full_messages = [
            {
                'role': 'system',
                'content': system_prompt
            }
        ] + messages
        
        # 定义流式生成函数
        def generate():
            try:
                # 调用OpenAI API，启用流式输出
                response = client.chat.completions.create(
                    model='Qwen/Qwen3-235B-A22B-Instruct-2507',
                    messages=full_messages,
                    stream=True
                )
                
                # 逐块发送数据
                for chunk in response:
                    if chunk.choices[0].delta.content:
                        content = chunk.choices[0].delta.content
                        # 使用SSE格式发送
                        yield f"data: {json.dumps({'content': content}, ensure_ascii=False)}\n\n"
                
                # 发送完成标记
                yield "data: [DONE]\n\n"
                
            except Exception as e:
                print(f"[AI对话] 生成错误: {str(e)}")
                import traceback
                traceback.print_exc()
                yield f"data: {json.dumps({'error': str(e)}, ensure_ascii=False)}\n\n"
        
        # 返回流式响应
        return Response(
            stream_with_context(generate()),
            mimetype='text/event-stream',
            headers={
                'Cache-Control': 'no-cache',
                'X-Accel-Buffering': 'no'
            }
        )
        
    except Exception as e:
        import traceback
        traceback.print_exc()
        return jsonify({
            'status': 'error',
            'message': f'对话失败: {str(e)}'
        }), 500

if __name__ == '__main__':
    app.run(debug=True)
