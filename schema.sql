DROP TABLE IF EXISTS `user`;
CREATE TABLE `user` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `name` varchar(255) DEFAULT NULL,
  `token` varchar(255) DEFAULT NULL,
  `leader_card_id` int DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `token` (`token`)
);

DROP TABLE IF EXISTS `rooms`;
CREATE TABLE `rooms` (
  `id` bigint NOT NULL AUTO_INCREMENT,
  `live_id` int NOT NULL,
  `status` int NOT NULL,
  `host` bigint NOT NULL,
  `count` int NOT NULL,
  PRIMARY KEY (`id`)
);

DROP TABLE IF EXISTS `members`;
CREATE TABLE `members` (
  `room_id` bigint NOT NULL,
  `user_id` bigint NOT NULL,
  `difficulty` int NOT NULL,
  `score` bigint DEFAULT NULL,
  `judge0` bigint DEFAULT NULL,
  `judge1` bigint DEFAULT NULL,
  `judge2` bigint DEFAULT NULL,
  `judge3` bigint DEFAULT NULL,
  `judge4` bigint DEFAULT NULL,
  PRIMARY KEY (`room_id`,`user_id`)
)