from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `login_failures` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `email` VARCHAR(100) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    KEY `idx_login_failu_email_08d632` (`email`)
) CHARACTER SET utf8mb4;
        ALTER TABLE `users` ADD UNIQUE INDEX `phone_number` (`phone_number`);
        ALTER TABLE `users` ADD UNIQUE INDEX `email` (`email`);"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        ALTER TABLE `users` DROP INDEX `email`;
        ALTER TABLE `users` DROP INDEX `phone_number`;
        DROP TABLE IF EXISTS `login_failures`;"""


MODELS_STATE = (
    "eJztXVtzo7gS/iuUn3arcrZsbMeXqvNAbJJ44kDWl52tHU9RGGSHHQxewDOTszX//aiFuV"
    "8CvuPhxYCkFuiTLLq/Vot/KytdRqr5G4MMRXqtdKl/K5q4QvgklHNDVcT12kuHBEucq6So"
    "6JWZm5YhShZOXYiqiXCSjEzJUNaWoms4VduoKiTqEi6oaEsvaaMp/2yQYOlLZL0iA2d8+o"
    "yTFU1G35HpXK6/CAsFqXLgURUZ7k3SBettTdIGmnVPCsLd5oKkq5uV5hVev1mvuuaWVjQL"
    "UpdIQ4ZoIajeMjbw+PB023Y6LbKf1CtiP6JPRkYLcaNavuZmxEDSNcAPP41JGriEu/yHrj"
    "VajXb9ttHGRciTuCmtH3bzvLbbggQBblL5QfJFS7RLEBg93L4iw4RHioDXexWNePR8IiEI"
    "8YOHIXQAS8PQSfBA9AbOgVBcid8FFWlLCwY43WymYPYHM+o9MqNfcKlfoTU6Hsz2GOe2Wb"
    "SdB8B6QMJfIweI2+LFBLBWrWYAEJdKBJDkBQHEd7SQ/R8MgvhhzHPxIPpEQkBONdzAT7Ii"
    "WTeUqpjW58uENQVFaDU89Mo0/1H94P3yzPwZxrU35O8ICrppLQ1SC6ngDmMMU+bii+/PDw"
    "lzUfryTTRkIZKj03pS2WjWil6FU0RNXBKsoMXQvu1LZGqSCT3yciHpqa+WDS5hXtab5U5Z"
    "XtHLpUPT9XqLrtZv281Gq9VsV923TDQr7XVzN3iAN05gbL7/CkIrUVHzzJ2uwGFmz6OjfP"
    "y581U0X5EsrEXT/KYbMQM2GcwY0YK+lOh2FmDpdjKwkBcElhxzoOmULyaEzSxDs5k8MpuR"
    "gYlbLNvzexRBVtusCIoD/EiiJqEImp70mfGsPDNDtkvB70y7Z+0r+1jZAefbDDDfJqJ8Gw"
    "Z5rhjWqyy+RWHuY3DiB6pfJgQunqiRpazQb3BymcM2Bb8+M2FD+Kxx65CAR9s8aSjGYxSW"
    "22kQbl8m53rbZBlqteSxVosMNk2EJxJVxYoZb2kTY0DsIFCe3G7MYjUm24xhJNcGWiDDwC"
    "9fVdSWG6w27zpPxtd0ujmz8kWvROfMJ75LfdFn2gemS/0tzrS/HrvU/15nGst1KaTtMm8e"
    "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"
    "iYUmm8Bt3CVhr3Cijbdyr/8X+gfkNF"
)
