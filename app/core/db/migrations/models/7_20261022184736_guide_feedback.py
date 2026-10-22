from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `guide_feedback` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `rating` VARCHAR(4) NOT NULL COMMENT 'UP: UP\nDOWN: DOWN',
    `reason` VARCHAR(18) COMMENT 'WRONG_INFO: WRONG_INFO\nHARD_TO_UNDERSTAND: HARD_TO_UNDERSTAND\nNOT_RELEVANT: NOT_RELEVANT\nOTHER: OTHER',
    `comment` VARCHAR(300),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `updated_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6) ON UPDATE CURRENT_TIMESTAMP(6),
    `guide_id` BIGINT NOT NULL UNIQUE,
    CONSTRAINT `fk_guide_fe_guides_ca1c5bbf` FOREIGN KEY (`guide_id`) REFERENCES `guides` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='가이드 1건에 대한 사용자 평가 (가이드당 1개, 다시 누르면 바뀐다)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `guide_feedback`;"""


MODELS_STATE = (
    "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"
    "8Ia6sAj9LkK/by30+5J8xcv/Afd/hu0="
)
