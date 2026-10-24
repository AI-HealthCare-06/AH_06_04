from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `hospital_contacts` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hospital_id` INT NOT NULL,
    `hospital_name` VARCHAR(100) NOT NULL,
    `contact_method` VARCHAR(20) NOT NULL COMMENT 'PHONE: phone\nMESSENGER: messenger\nEMAIL: email\nVISIT: visit',
    `status` VARCHAR(20) NOT NULL COMMENT 'REQUESTED: requested\nIN_PROGRESS: in_progress\nCOMPLETED: completed\nCANCELLED: cancelled' DEFAULT 'requested',
    `memo` VARCHAR(500),
    `record_id` BIGINT,
    `safety_alert_id` BIGINT,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_hospital_users_f7dce423` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='병원 연계 요청 1건';
        ALTER TABLE `ocr_jobs` MODIFY COLUMN `draft` JSON;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `ocr_jobs` MODIFY COLUMN `draft` JSON;
        DROP TABLE IF EXISTS `hospital_contacts`;"""


MODELS_STATE = (
    "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"
)
