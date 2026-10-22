from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `ocr_jobs` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `status` VARCHAR(7) NOT NULL COMMENT 'PENDING: PENDING\nDONE: DONE\nFAILED: FAILED' DEFAULT 'PENDING',
    `engine` VARCHAR(30) NOT NULL,
    `draft` JSON,
    `error_message` VARCHAR(200),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `finished_at` DATETIME(6),
    `used_at` DATETIME(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_ocr_jobs_users_1ad1c7c0` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방전·약봉투 사진 인식 작업 1건';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `ocr_jobs`;"""


MODELS_STATE = (
    "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"
)
