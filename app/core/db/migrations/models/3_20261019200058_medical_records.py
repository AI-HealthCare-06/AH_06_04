from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `medical_records` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `hospital_name` VARCHAR(100) NOT NULL,
    `visit_date` DATE NOT NULL,
    `procedure_name` VARCHAR(100),
    `doctor_note` LONGTEXT,
    `source` VARCHAR(6) NOT NULL COMMENT 'MANUAL: MANUAL\nOCR: OCR' DEFAULT 'MANUAL',
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_medical__users_aa3196ba` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='진료기록 1건 = 병원에 한 번 다녀온 기록 (받은 시술·의사 설명·처방을 함께 담음)';
        CREATE TABLE IF NOT EXISTS `prescription_items` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `drug_name` VARCHAR(100) NOT NULL,
    `dose` VARCHAR(50),
    `times_per_day` SMALLINT,
    `days` SMALLINT,
    `record_id` BIGINT NOT NULL,
    CONSTRAINT `fk_prescrip_medical__e075b4ce` FOREIGN KEY (`record_id`) REFERENCES `medical_records` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='처방 약 한 줄 = 영수증의 품목 한 줄';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `prescription_items`;
        DROP TABLE IF EXISTS `medical_records`;"""


MODELS_STATE = (
    "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"
    "CW06fDHY438swPWT"
)
