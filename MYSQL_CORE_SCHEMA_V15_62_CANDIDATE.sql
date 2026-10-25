-- Salah Archive MySQL 8.4 core schema candidate
-- Target database: salah_archive_test ONLY.
-- This file creates tables; it does not migrate records or touch the SQLite database.
-- Review before applying. No DROP/ALTER/DELETE statements are included.
SET NAMES utf8mb4;

CREATE TABLE IF NOT EXISTS local_cabinets (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(190) NOT NULL UNIQUE,
  description TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_documents (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  cabinet_id BIGINT NOT NULL,
  doc_type VARCHAR(40) NOT NULL DEFAULT 'other',
  document_number VARCHAR(255) NOT NULL DEFAULT '',
  document_date VARCHAR(32) NOT NULL DEFAULT '',
  subject VARCHAR(1000) NOT NULL DEFAULT '',
  sender_recipient VARCHAR(1000) NOT NULL DEFAULT '',
  employee_name VARCHAR(500) NOT NULL DEFAULT '',
  keywords TEXT,
  notes LONGTEXT,
  original_name VARCHAR(1024) NOT NULL,
  stored_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(255) DEFAULT 'application/octet-stream',
  file_size BIGINT NOT NULL DEFAULT 0,
  sha256 CHAR(64) NOT NULL,
  created_by VARCHAR(190) NOT NULL DEFAULT 'admin',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_local_docs_number (document_number),
  INDEX idx_local_docs_date (document_date),
  INDEX idx_local_docs_subject (subject(191)),
  INDEX idx_local_docs_sha (sha256),
  CONSTRAINT fk_local_documents_cabinet FOREIGN KEY(cabinet_id)
    REFERENCES local_cabinets(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_document_fields (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  document_id BIGINT NOT NULL,
  field_name VARCHAR(190) NOT NULL,
  field_value LONGTEXT,
  INDEX idx_local_document_fields_document (document_id),
  INDEX idx_local_document_fields_name (field_name),
  CONSTRAINT fk_local_document_fields_document FOREIGN KEY(document_id)
    REFERENCES local_documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_users (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(190) NOT NULL UNIQUE,
  display_name VARCHAR(190) NOT NULL DEFAULT '',
  password_salt CHAR(32) NOT NULL,
  password_hash CHAR(64) NOT NULL,
  role VARCHAR(20) NOT NULL DEFAULT 'viewer',
  is_active TINYINT NOT NULL DEFAULT 1,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT chk_local_users_role CHECK(role IN ('admin','editor','viewer'))
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_audit (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  username VARCHAR(190) NOT NULL,
  action VARCHAR(190) NOT NULL,
  document_id BIGINT NULL,
  details TEXT,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_local_audit_document (document_id),
  INDEX idx_local_audit_created (created_at)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_cases (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_number VARCHAR(190) NOT NULL UNIQUE,
  title VARCHAR(1000) NOT NULL,
  case_type VARCHAR(80) NOT NULL DEFAULT 'administrative',
  status VARCHAR(40) NOT NULL DEFAULT 'open',
  priority VARCHAR(40) NOT NULL DEFAULT 'normal',
  owner_department VARCHAR(255) DEFAULT '',
  assigned_to VARCHAR(255) DEFAULT '',
  due_date VARCHAR(32) DEFAULT '',
  notes LONGTEXT,
  created_by VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  updated_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_local_cases_status (status),
  INDEX idx_local_cases_number (case_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_case_events (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  event_type VARCHAR(100) NOT NULL,
  details TEXT,
  created_by VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_local_case_events_case (case_id),
  CONSTRAINT fk_local_case_events_case FOREIGN KEY(case_id)
    REFERENCES local_cases(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scan_baskets (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(190) NOT NULL UNIQUE,
  description TEXT,
  cabinet_id BIGINT NULL,
  default_doc_type VARCHAR(40) NOT NULL DEFAULT 'incoming',
  is_active TINYINT NOT NULL DEFAULT 1,
  created_by VARCHAR(190) NOT NULL DEFAULT 'admin',
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_scan_baskets_cabinet FOREIGN KEY(cabinet_id)
    REFERENCES local_cabinets(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scan_inbox (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  basket_id BIGINT NOT NULL,
  original_name VARCHAR(1024) NOT NULL,
  stored_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(255) DEFAULT 'application/pdf',
  file_size BIGINT NOT NULL DEFAULT 0,
  sha256 CHAR(64) NOT NULL,
  status VARCHAR(32) NOT NULL DEFAULT 'pending',
  extracted_text LONGTEXT,
  ai_suggestion LONGTEXT,
  created_by VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_scan_inbox_basket (basket_id,status),
  CONSTRAINT fk_scan_inbox_basket FOREIGN KEY(basket_id)
    REFERENCES scan_baskets(id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


CREATE TABLE IF NOT EXISTS scan_inbox_groups (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  basket_id BIGINT NOT NULL,
  created_by VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  INDEX idx_scan_inbox_groups_basket (basket_id),
  CONSTRAINT fk_scan_inbox_groups_basket FOREIGN KEY(basket_id)
    REFERENCES scan_baskets(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS scan_inbox_group_items (
  group_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  PRIMARY KEY(group_id,inbox_id),
  UNIQUE KEY uq_scan_inbox_group_item_inbox (inbox_id),
  CONSTRAINT fk_scan_inbox_group_items_group FOREIGN KEY(group_id)
    REFERENCES scan_inbox_groups(id) ON DELETE CASCADE,
  CONSTRAINT fk_scan_inbox_group_items_inbox FOREIGN KEY(inbox_id)
    REFERENCES scan_inbox(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_case_inbox_links (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  inbox_id BIGINT NOT NULL,
  linked_by VARCHAR(190) NOT NULL,
  linked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_case_inbox (case_id,inbox_id),
  CONSTRAINT fk_case_inbox_case FOREIGN KEY(case_id)
    REFERENCES local_cases(id) ON DELETE CASCADE,
  CONSTRAINT fk_case_inbox_inbox FOREIGN KEY(inbox_id)
    REFERENCES scan_inbox(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_case_documents (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  document_id BIGINT NOT NULL,
  linked_by VARCHAR(190) NOT NULL,
  linked_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  UNIQUE KEY uq_case_document (case_id,document_id),
  CONSTRAINT fk_case_documents_case FOREIGN KEY(case_id)
    REFERENCES local_cases(id) ON DELETE CASCADE,
  CONSTRAINT fk_case_documents_document FOREIGN KEY(document_id)
    REFERENCES local_documents(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS local_case_attachments (
  id BIGINT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  case_id BIGINT NOT NULL,
  original_name VARCHAR(1024) NOT NULL,
  stored_name VARCHAR(255) NOT NULL,
  mime_type VARCHAR(255) DEFAULT 'application/octet-stream',
  file_size BIGINT NOT NULL DEFAULT 0,
  notes TEXT,
  added_by VARCHAR(190) NOT NULL,
  created_at DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
  CONSTRAINT fk_local_case_attachments_case FOREIGN KEY(case_id)
    REFERENCES local_cases(id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;


-- MySQL search index mirror used by mysql_index_sync.py
CREATE TABLE IF NOT EXISTS archive_index (
  document_id BIGINT NOT NULL PRIMARY KEY,
  cabinet_id BIGINT NULL,
  cabinet_name VARCHAR(255) NULL,
  doc_type VARCHAR(40) NULL,
  document_number VARCHAR(255) NULL,
  document_date VARCHAR(32) NULL,
  subject TEXT NULL,
  sender_recipient TEXT NULL,
  employee_name TEXT NULL,
  keywords TEXT NULL,
  notes LONGTEXT NULL,
  original_name VARCHAR(1024) NULL,
  stored_name VARCHAR(255) NULL,
  mime_type VARCHAR(255) NULL,
  file_size BIGINT NULL,
  sha256 CHAR(64) NULL,
  created_by VARCHAR(190) NULL,
  created_at VARCHAR(32) NULL,
  updated_at VARCHAR(32) NULL,
  indexed_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  INDEX idx_archive_number (document_number),
  INDEX idx_archive_date (document_date),
  INDEX idx_archive_sha (sha256)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS archive_index_fields (
  document_id BIGINT NOT NULL,
  field_name VARCHAR(190) NOT NULL,
  field_value LONGTEXT NULL,
  PRIMARY KEY(document_id,field_name),
  INDEX idx_archive_field_name(field_name),
  CONSTRAINT fk_archive_index_fields_document FOREIGN KEY(document_id)
    REFERENCES archive_index(document_id) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
