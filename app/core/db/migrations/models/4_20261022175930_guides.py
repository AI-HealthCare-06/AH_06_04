from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `guides` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `language` VARCHAR(2) NOT NULL COMMENT 'KO: ko\nJA: ja\nZH: zh\nEN: en' DEFAULT 'ko',
    `status` VARCHAR(9) NOT NULL COMMENT 'PENDING: PENDING\nDONE: DONE\nNO_SOURCE: NO_SOURCE\nFAILED: FAILED' DEFAULT 'PENDING',
    `medication_guide` LONGTEXT,
    `lifestyle_guide` LONGTEXT,
    `llm_model` VARCHAR(50),
    `error_message` VARCHAR(200),
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    `generated_at` DATETIME(6),
    `record_id` BIGINT,
    `user_id` BIGINT NOT NULL,
    CONSTRAINT `fk_guides_medical__532b52ea` FOREIGN KEY (`record_id`) REFERENCES `medical_records` (`id`) ON DELETE SET NULL,
    CONSTRAINT `fk_guides_users_73e91131` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='AI 가이드 1건';
        CREATE TABLE IF NOT EXISTS `guide_sources` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `doc_id` VARCHAR(100) NOT NULL,
    `document_title` VARCHAR(200) NOT NULL,
    `url` VARCHAR(500),
    `relevance_score` DOUBLE NOT NULL,
    `guide_id` BIGINT NOT NULL,
    CONSTRAINT `fk_guide_so_guides_eb075572` FOREIGN KEY (`guide_id`) REFERENCES `guides` (`id`) ON DELETE CASCADE
) CHARACTER SET utf8mb4 COMMENT='가이드가 참고한 근거 안내문 1개 (출처 표시용)';"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `guide_sources`;
        DROP TABLE IF EXISTS `guides`;"""


MODELS_STATE = (
    "eJztXWuTorga/iuUn2ar5mwp7b3qfECle9zxMqX2nq1Zt6gYonIaweUyM717+r+fJCjXQI"
    "OtIr18EUjyhuTJm+S9Bf+u7HQZqebPAjIUuK10ub8rGtghfBPK+chVwH7vpZMEC6xUWhR4"
    "ZVamZQBo4dQ1UE2Ek2RkQkPZW4qu4VTNVlWSqENcUNE2XpKtKX/aSLL0DbK2yMAZv/+Bkx"
    "VNRj+QeXzcP0lrBalyoKmKTN5N0yXreU/Thpp1TwuSt60kqKv2TvMK75+tra65pRXNIqkb"
    "pCEDWIhUbxk2aT5p3aGfxx45LfWKOE300choDWzV8nU3JQZQ1wh+uDUm7eCGvOVffK3eqr"
    "fvmvU2LkJb4qa0XpzueX13CCkCk0XlheYDCzglKIwebt+QYZImRcDrb4HBRs9HEoIQNzwM"
    "4RGwJAyPCR6IHuOcCcUd+CGpSNtYhMH5RiMBs1+FWf+TMPuAS/1EeqNjZnZ4fHLI4p08Aq"
    "wHJJkaGUA8FC8mgLVqNQWAuFQsgDQvCCB+o4WcORgE8Zf5dMIG0UcSAlJWoMX9j1MVMzKp"
    "bwPQBPxIf0mjd6b5p+qH7cNY+C2MaH807dH+66a1MWgttIIeRpcslusn37QnCSsAn74DQ5"
    "YiOTqvx5WNZu34XTgFaGBDsSI9Jv07bB+PJl3KI9sKTU/cVGxcwrytPaWnbN7RttLh+bu7"
    "Fl+9a7Yb9Var0a66+0s0K2mj6Q0fyF4T4M3XNx+0A4qaZdV0CYq5btbTLJv1+FWzHlk0t8"
    "DcIlnaA9P8rhsMfo3HkkFaTFRrfDvNbsS343cjkhcEll4zoHksX0wI+TSMycczJh9hTNxj"
    "2VneowiKmr2jKA5xk4AGUQRNjzpnPCtjYSR2OfK71O5F58m5Vk7AuZkC5mYsys0wyCvFsL"
    "YyeI7CPMDgsBnVTxMWmjCRpezQz+TmNtk2Ab+BsBBD+Oxx75CEuW0Vx4psjMJ0xZzUtVqa"
    "ZbEWvyrWwvymmBIWwpRvjJWxp+sqAlqMYOSnC4G5woSXQtMVms7Na73pdBQQ0XvDkPAzeR"
    "z3RAwvRRcXUqyATBTEVN4pDA38VUiPZFdENKv0nQukKjAtSdU3LFAHhzWOjWqQMml5JDcp"
    "QD5w4G2skIvhWJwvhPGXAM5k3SQ5PE19DqVGtiO3Eu4/w8UnjjxyX6cTMayEuuUWXyukTc"
    "C2dEnTv2O29Xf7mHxMCpoEDESglQDDKpA8kEHKMwxkHqs57oM81dTnAx8VZGQPLJ84sPZe"
    "PnFgg5TlwOY6sLTxGaxMHgMYaEfwNSQTWRbGymRsf4cq7j/PkAostsX5YEqaHaqbO7Xd5r"
    "C/HHn5mOoNv882hmQFAlUyEMRK+RthGTuVzWhdBQZlYyu4+rdh8UDqKBgGl7TKhqcMw0DL"
    "mFXxtlrmjC7ttu/SbuuONQUrgnU6G0+kktxNPeJg2BcWw+mky3n3S+3hcTgQpf4nsf+5y/"
    "keTjEAnV8nN+EWybaKZ4rCslgmS1MR4mIKVAURoFLpPAbaY9VFMvCoZDFZhchOmkvXV1Yv"
    "bYUuDVbnt66USvm70N0YSrmJN+OsspOP6HUB6kaG8GoyVEQ1DoIdRfpeN5Cy0T6j54jsxN"
    "ZqjjEUt4dynFKDkw3w3ZXa/QyEu4c7hZyFpy/M+8JArLzkE7TSd0KL8IDsgCWYWKmpMDQk"
    "RqmPSUrSIWBJWlMCCRCKCyhKvzsa83EyOy+jnPNHqUPdiA4VGKHUMPupyvU2ireHr5/rmX"
    "L06xpqqIq89VPhcTCcdjl6WWq/Yj0UP9HLUhuOhQexy9HLKXppmoDY+HDYSDDsWsE6pW1k"
    "iu3y0xTT4d5IFRbbSAiLbTDCYktx+/2I2zcSkRv0CzDkmojjIF6kYTgsXhVmKksbdmB9aa"
    "/aEC5tgO6q5L4hczX8BFt17t8cToAyfoRNGWfChlzFSXKjAWlOu00uPCJ11OqkQJMnSb6q"
    "PpBytRXOatUJLeRlSH55XKBaXbVIRqONf6uA1AlrPKkMtBtuNuy0SR18h9ZRp+9vtslLZO"
    "f16zrNgT+Fl9x32cHSIp+3dBMvTW51c69YeBpmjVuNEBZz673IiZRviqlY0jEYMm2AZZDq"
    "3YdYGjpEsm2gzJwXpSyk0foinIcbYekGFh1YrLdAP2KWzRBZQfBMkunE3xYBcS5yFMoV6U"
    "bTycOxePh8VMhjptsGPFkp9Kivt1JWxsLkUaAG/Eh4OskgAerkutSm/VmXwz+n6IBnDk4v"
    "FZd3pLiUwXvvbmAjUVal/+fcEnvp/7mo/8enX1po98b4wC+G188hrq5YqOYWLpmbuHjdaM"
    "kIdzCMZiwOireb7X2lJZd/U5nOXLMNseo0WrJnN4KdqmNags0qMS3xNWL/6XRkxxZECtbb"
    "hBiATpCKZcG61HtKQ9LtGpJkw95kVuUDRKUByafGm9lwPJQviOIe9n6lcn4l+L7C8BElwJ"
    "T2WD5gnnGe74Cqxs78CPFJ4mkOoDrLwB3faroTnzwkTfX5WBiNoi5w3HGGFJAM25Hmn4eW"
    "48DKrAAFyEoVKIMKZLjexTcqQQU+5vQxpA0FuOmW4uEcfYAh9bqKQryo6+kjr4u3wpA4OW"
    "GVeDxbLeKwrMvw6DWNCKmvli5FzdsVNVWgbWzMbada4v30V7TFP+kMO/znaZd70pfaL0KX"
    "+y9Yal8/dbm/tktNnHQ5pJ1ijefTnIWIPwoROSZkActmSAMpnR4u9RWB/iJOBsPJAwPtQ0"
    "6XO9wstcF0InY58rvUJlNpPn2c9XGCe7vU7oXhSBx0Oed6yoh0UoxIJ3ZEOuERcQJnqPq/"
    "Oa6haR19LNqCKA3X9vapyhqZ1rOKsqPMIC1BZoOs7iS68WfRdgNEBQH20iovMgzdkLDmas"
    "ZujGwwI4SFBJRPZYXhE6wwfBlB+079lVFHtAv2CUMbpi2/9ZT7ueeczC+5Ga2ufCCmdO+f"
    "G93SvX8G9350DcjBIng7XuwwfvEGwbm44CaPo1G6CAknbPEcQQFzNwCyOFx50dgAPypxBl"
    "IPtFfMpJJvoNIEA4SNn04KcbbDO3KSA6Kq638H8prmt2h+o04c9NUVIVzdtR2raQ2SYyVQ"
    "7kDH/089+Q3oHi5pgg7rsEtOrSitu3mLFwmBBDpkShtJ3m/IFjX+2SEE0N6RTwZYipXti0"
    "BRymLCehGbQMazyW85lpy3TeUip5INLIZ8IzKYZGL5hMGX96oOYlW2CG0I2DUhvk3eTDod"
    "NX3sjUTuy0zsD+fDw3/4uDo2zSRJ3reVZqIwCv9tQvlViGuqaTEugcz6RgE/LhpWNPw8lH"
    "/gwcv/AUBIAOw="
)
