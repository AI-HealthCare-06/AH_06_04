from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `hospital_contact_messages` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `sender` VARCHAR(10) NOT NULL COMMENT 'PATIENT: patient\nHOSPITAL: hospital',
    `body` VARCHAR(500) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `contact_id` BIGINT NOT NULL,
    CONSTRAINT `fk_hospital_hospital_9771b053` FOREIGN KEY (`contact_id`) REFERENCES `hospital_contacts` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='[11/3] 상담 요청 1건 안에서 환자 ↔ 병원이 주고받는 메시지 — 연락처 교환 없이 앱 안에서 끝낸다';
        ALTER TABLE `reminder_settings` MODIFY COLUMN `reminder_type` VARCHAR(11) NOT NULL COMMENT 'MEDICATION: MEDICATION\nTOPICAL: TOPICAL\nGUIDE_CHECK: GUIDE_CHECK';
        ALTER TABLE `hospital_contacts` ADD `appointment_at` DATETIME(6);
        ALTER TABLE `hospital_contacts` MODIFY COLUMN `contact_method` VARCHAR(20) NOT NULL COMMENT 'PHONE: phone\nMESSENGER: messenger\nEMAIL: email\nVISIT: visit\nAPP: app';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `reminder_settings` MODIFY COLUMN `reminder_type` VARCHAR(11) NOT NULL COMMENT 'MEDICATION: MEDICATION\nGUIDE_CHECK: GUIDE_CHECK';
        ALTER TABLE `hospital_contacts` DROP COLUMN `appointment_at`;
        ALTER TABLE `hospital_contacts` MODIFY COLUMN `contact_method` VARCHAR(20) NOT NULL COMMENT 'PHONE: phone\nMESSENGER: messenger\nEMAIL: email\nVISIT: visit';
        DROP TABLE IF EXISTS `hospital_contact_messages`;"""


MODELS_STATE = (
    "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"
    "gnB+mOe1d/ZHVPnBIM//B3A/yLk="
)
