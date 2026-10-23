from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `preferred_language` VARCHAR(2) NOT NULL COMMENT 'KO: ko\nJA: ja\nZH: zh\nEN: en' DEFAULT 'ko';
        ALTER TABLE `users` ADD `nationality` VARCHAR(2);
        ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(16);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `preferred_language`;
        ALTER TABLE `users` DROP COLUMN `nationality`;
        ALTER TABLE `users` MODIFY COLUMN `phone_number` VARCHAR(11) NOT NULL;"""


MODELS_STATE = (
    "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"
)
