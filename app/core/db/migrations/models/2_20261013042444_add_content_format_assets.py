from tortoise import BaseDBAsyncClient

RUN_IN_TRANSACTION = True


async def upgrade(db: BaseDBAsyncClient) -> str:
    return """
        CREATE TABLE IF NOT EXISTS `content_format_assets` (
    `id` BIGINT NOT NULL PRIMARY KEY AUTO_INCREMENT,
    `guide_id` BIGINT NOT NULL,
    `format_type` VARCHAR(5) NOT NULL COMMENT 'AUDIO: AUDIO\nVIDEO: VIDEO\nIMAGE: IMAGE',
    `file_url` VARCHAR(500) NOT NULL,
    `created_at` DATETIME(6) NOT NULL DEFAULT CURRENT_TIMESTAMP(6),
    UNIQUE KEY `uid_content_for_guide_i_4fbc9f` (`guide_id`, `format_type`)
) CHARACTER SET utf8mb4;"""


async def downgrade(db: BaseDBAsyncClient) -> str:
    return """
        DROP TABLE IF EXISTS `content_format_assets`;"""


MODELS_STATE = (
    "eJztml9P4zgQwL9Klac9iVvR0EKPt7QNkIO2Jyh7pwUUuY2bWiRON3aWrVZ897OdpPnnhB"
    "QBbVFfSDOeSeyfJ+MZ49+K61nQIV816KPpXDlt/FYwcCH7kWs5aChgsUjkXEDBxBGqINGZ"
    "EOqDKWXSGXAIZCILkqmPFhR5mElx4Dhc6E2ZIsJ2Igow+hFAk3o2pHPos4a7ByZG2IK/II"
    "lvF4/mDEHHynQVWfzdQm7S5ULIDEzPhCJ/28Scek7g4kR5saRzD6+0EaZcakMMfUAhfzz1"
    "A9593rtonPGIwp4mKmEXUzYWnIHAoanh1mQw9TDnx3pDxABt/pY/1WbrpNU5Om51mIroyU"
    "py8hwOLxl7aCgIDMfKs2gHFIQaAmPC7Sf0Ce9SAV5vDnw5vZRJDiHreB5hDKyKYSxIICaO"
    "80YUXfDLdCC2KXdwtd2uYPZNu+5daNdfmNYffDQec+bQx4dRkxq2cbAJSP5prAExUt9NgM"
    "3DwxoAmVYpQNGWBcjeSGH4DWYh/n0zGsohpkxyIG8xG+Cdhab0oOEgQh+2E2sFRT5q3mmX"
    "kB9OGt6XgfZfnmvvatQVFDxCbV88RTygyxjzkDl7TH38XDAB08cn4FtmocVTvTLdYpOrun"
    "kJwMAWrPiI+fiiReSWiIBeWFyEvHJpCZgG2a6VpYvsT7S4/KWqR0cn6uHRcafdOjlpdw5X"
    "q0yxqWq56RrnfMXJ+ObLSxB0AXLWiZ0rg92Mnq06wbNVHjtbhdA5B2QOLXMBCHnyfIm/lr"
    "OUmO4m1abaqbMmqZ3yNYm3ZcGK6xo0Y/3dRKjWcUy13DHVgmOyEVtheC8S1HHgCooG6xLA"
    "U1igmVhvmKcy0K700wb/e4/P9PAuvCqv4HxcA/NxKeXjPOQJ8uncAssi5j6DI3fUtE0OLo"
    "vTkCIXfuU/ttNtK/j1tbGe47Ngo4Mm87ZJmSvKGeXtdvOjbjbrhMVmeVRs5v0NEZMlYein"
    "JDJ2Pc+BAJckRmm7HMwJM3wvmquk6a19rTsaXWVS9K6RS36Gt4OuzvAKukwJ0UxOlGVquU"
    "hSh7+INDb7QKLrZt8bQeoAQk3Hs2VQ+1GMk1PNWlaFR/6jBuTIA7cjQo6NgX4z1gb/ZDjz"
    "uMlbVCFd5qSF5Wj1kMa/xviiwW8b30dDPV+ErvTG3xXeJxBQz8TeE3Pb9LBjcSzKbgz4kK"
    "M1gWRvoHois5ZvMJGbiOZsDNYIO8vIj3ZkZiOXr5zYYGG9cmKzlvuJ3ejEis6vscuUOIAP"
    "Xc7XNwmklLEikuUvesTZ5TV0AJXvO0dbSdfR427Cp23ntD/HvhxL0wTfa/MtT0ayDyeBV7"
    "4lJ524/fbcp9yeW821gFVgXa+ULzxk4xW93jd62tgYDVldv/p9j89vjb5u9i703uVpI3Xz"
    "mjr/7UsvMp1DK3DYl4JkG1PVi2bBeDfXzR1ZJ2ultj5csAzV9NmsrLMzkTN71bf08TXJe2"
    "827vcl3r6I3tdenyJFl9RehC3G6+ZOKaOXE6gtmcIPy6EKFVAWdpH0medDZONLuCzkTvL6"
    "Jv5X+fZRLitqmNgHT6usPe1AbHhsUDAMPD3tpqf1deV5M2cTeuE5EjYhLqAaYUWNIqmQJF"
    "oHVUVSdDrFnAkDE3CLdyiU7hQ7QBaMP+bwZcJzHvY11JbUUJkZqo05bbWPt0XeCd+010vz"
    "6Jcr1NwjNl2fard9Y3TaEJd7/I3VoexOXO6xMdDO9dOGuLymLq1z+rH87GPh5OMMsZoy8N"
    "c6wpO22c3/q7ZrnYFsV5yBbEvOQO7T7c+Tbm/04OXz/8JsR58="
)
