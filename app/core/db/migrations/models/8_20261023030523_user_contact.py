from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` ADD `messenger_type` VARCHAR(10) COMMENT 'WECHAT: WECHAT\nLINE: LINE\nWHATSAPP: WHATSAPP\nKAKAOTALK: KAKAOTALK\nTELEGRAM: TELEGRAM';
        ALTER TABLE `users` ADD `messenger_id` VARCHAR(50);
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(100) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(50) NOT NULL;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP COLUMN `messenger_type`;
        ALTER TABLE `users` DROP COLUMN `messenger_id`;
        ALTER TABLE `users` MODIFY COLUMN `email` VARCHAR(40) NOT NULL;
        ALTER TABLE `users` MODIFY COLUMN `name` VARCHAR(20) NOT NULL;"""


MODELS_STATE = (
    "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"
)
