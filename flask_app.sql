-- 新的表结构
-- 1. 来源表
CREATE TABLE `source_articles` (
  `sid` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'HTML内容',
  `author_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cover_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_type` enum('WECHAT','TEJIAN','WUHU') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `process_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT '处理状态：0-待处理, 1-已处理, 4-已舍弃',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`sid`),
  UNIQUE KEY `uk_source_url` (`source_url`),
  KEY `idx_source_type` (`source_type`),
  KEY `idx_process_status` (`process_status`),
  KEY `idx_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='接口来源表-原始文章数据';

-- 2. 标准化表
CREATE TABLE `normalized_articles` (
  `nid` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `sid` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL COMMENT 'Markdown内容',
  `author_name` varchar(80) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `cover_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `source_type` enum('WECHAT','TEJIAN','WUHU') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `distribution_mark` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'W',
  `process_status` tinyint(1) NOT NULL DEFAULT 0 COMMENT '处理状态：0-待处理, 1-已处理, 4-已舍弃',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`nid`),
  UNIQUE KEY `uk_sid` (`sid`),
  KEY `idx_distribution_mark` (`distribution_mark`),
  KEY `idx_process_status` (`process_status`),
  CONSTRAINT `fk_source_article`
    FOREIGN KEY (`sid`) REFERENCES `source_articles` (`sid`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='文章标准化表-Markdown格式';

-- 3. 发布表
CREATE TABLE `publish_articles` (
  `pid` bigint(20) UNSIGNED NOT NULL AUTO_INCREMENT,
  `nid` bigint(20) UNSIGNED NOT NULL,
  `title` varchar(200) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `content_html` longtext CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `cover_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_url` varchar(500) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_platform` enum('BILIBILI','XIAOHONGSHU','ZHIHU','DOUYIN','WEIXIN','TEJIAN') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `publish_status` tinyint(1) NOT NULL DEFAULT 0,
  `platform_article_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`pid`),
  KEY `idx_nid` (`nid`),
  KEY `idx_target_platform` (`target_platform`),
  KEY `idx_publish_status` (`publish_status`),
  KEY `idx_updated_at` (`updated_at`),
  CONSTRAINT `fk_normalized_article`
    FOREIGN KEY (`nid`) REFERENCES `normalized_articles` (`nid`) ON DELETE RESTRICT
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='最终发布表-多平台HTML格式';

-- 3. 网站发布表
CREATE TABLE `website_articles` (
  `wid` bigint(20) unsigned NOT NULL AUTO_INCREMENT,
  `nid` bigint(20) unsigned NOT NULL,
  `title` varchar(200) COLLATE utf8mb4_unicode_ci NOT NULL,
  `content` longtext COLLATE utf8mb4_unicode_ci NOT NULL,
  `cover_url` varchar(500) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `source_url` varchar(500) COLLATE utf8mb4_unicode_ci NOT NULL,
  `target_platform` enum('BILIBILI','XIAOHONGSHU','ZHIHU','DOUYIN','WEIXIN','TEJIAN') COLLATE utf8mb4_unicode_ci NOT NULL,
  `publish_status` tinyint(1) NOT NULL DEFAULT '0',
  `platform_article_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`wid`)
) ENGINE=InnoDB AUTO_INCREMENT=14 DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci COMMENT='网站发布表'