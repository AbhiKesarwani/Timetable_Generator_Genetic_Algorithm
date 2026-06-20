-- run_queries.sql
-- Use this script to seed the database with test data for "School of Developers"

USE timetable_db;

SET FOREIGN_KEY_CHECKS = 0;

-- 1. Create a new school: "School of Developers"
-- Password 'test' hashed using Werkzeug (pbkdf2:sha256)
INSERT INTO `schools` (`school_name`, `username`, `password_hash`, `start_time`, `end_time`, `lecture_duration`, `break_start_time`, `break_duration`) 
VALUES (
    'School of Developers', 
    'test', 
    'scrypt:32768:8:1$9pKNRyRMOG8d2fkM$aed0bcef59a339791d55026d6ae8afdefa38e2c69074510a5273ff2480085352b26aecd0ffe4db300bb75098c164063382a01313234644d0dbb1d871def33c93', 
    '09:00', '17:00', 60, '12:00', 60
);

SET @school_id = LAST_INSERT_ID();

-- 2. Create a default course
INSERT INTO `course` (`course_name`, `school_id`) VALUES ('Computer Science', @school_id);
SET @course_id = LAST_INSERT_ID();

-- 3. Create 4 Classes
INSERT INTO `class` (`class_name`, `school_id`) VALUES ('FRONTEND FY', @school_id);
SET @class_fe = LAST_INSERT_ID();

INSERT INTO `class` (`class_name`, `school_id`) VALUES ('BACKEND SY', @school_id);
SET @class_be = LAST_INSERT_ID();

INSERT INTO `class` (`class_name`, `school_id`) VALUES ('DEVOPS TY', @school_id);
SET @class_do = LAST_INSERT_ID();

INSERT INTO `class` (`class_name`, `school_id`) VALUES ('AI & ML BTech', @school_id);
SET @class_ai = LAST_INSERT_ID();

-- 4. Create Teachers and Subjects for FRONTEND FY
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Ada Lovelace', @school_id); SET @t1 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Brendan Eich', @school_id); SET @t2 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Håkon Wium Lie', @school_id); SET @t3 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('John Resig', @school_id); SET @t4 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Jordan Walke', @school_id); SET @t5 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Evan You', @school_id); SET @t6 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Dan Abramov', @school_id); SET @t7 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Lea Verou', @school_id); SET @t8 = LAST_INSERT_ID();

INSERT INTO `subject` (`subject_name`, `class_id`, `course_id`, `teacher_id`, `semester`, `credits`, `school_id`) VALUES 
('HTML5 Basics', @class_fe, @course_id, @t1, 1, 4, @school_id),
('JavaScript ES6', @class_fe, @course_id, @t2, 1, 4, @school_id),
('Modern CSS', @class_fe, @course_id, @t3, 1, 4, @school_id),
('jQuery Legacy', @class_fe, @course_id, @t4, 1, 3, @school_id),
('React Fundamentals', @class_fe, @course_id, @t5, 1, 5, @school_id),
('VueJS Core', @class_fe, @course_id, @t6, 1, 4, @school_id),
('Redux State', @class_fe, @course_id, @t7, 1, 3, @school_id),
('Web Accessibility', @class_fe, @course_id, @t8, 1, 3, @school_id);

-- 5. Create Teachers and Subjects for BACKEND SY
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('James Gosling', @school_id); SET @t9 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Guido van Rossum', @school_id); SET @t10 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Dennis Ritchie', @school_id); SET @t11 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Bjarne Stroustrup', @school_id); SET @t12 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Ryan Dahl', @school_id); SET @t13 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Martin Fowler', @school_id); SET @t14 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Robert Martin', @school_id); SET @t15 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Joshua Bloch', @school_id); SET @t16 = LAST_INSERT_ID();

INSERT INTO `subject` (`subject_name`, `class_id`, `course_id`, `teacher_id`, `semester`, `credits`, `school_id`) VALUES 
('Java Core', @class_be, @course_id, @t9, 3, 5, @school_id),
('Python Advanced', @class_be, @course_id, @t10, 3, 5, @school_id),
('C Programming', @class_be, @course_id, @t11, 3, 4, @school_id),
('C++ Systems', @class_be, @course_id, @t12, 3, 4, @school_id),
('NodeJS Runtime', @class_be, @course_id, @t13, 3, 4, @school_id),
('Microservices', @class_be, @course_id, @t14, 3, 3, @school_id),
('Clean Code', @class_be, @course_id, @t15, 3, 3, @school_id),
('API Design', @class_be, @course_id, @t16, 3, 3, @school_id);

-- 6. Create Teachers and Subjects for DEVOPS TY
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Linus Torvalds', @school_id); SET @t17 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Solomon Hykes', @school_id); SET @t18 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Brendan Burns', @school_id); SET @t19 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Mitchell Hashimoto', @school_id); SET @t20 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Gene Kim', @school_id); SET @t21 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Werner Vogels', @school_id); SET @t22 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Kelsey Hightower', @school_id); SET @t23 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Nicole Forsgren', @school_id); SET @t24 = LAST_INSERT_ID();

INSERT INTO `subject` (`subject_name`, `class_id`, `course_id`, `teacher_id`, `semester`, `credits`, `school_id`) VALUES 
('Linux Kernel', @class_do, @course_id, @t17, 5, 5, @school_id),
('Docker Containers', @class_do, @course_id, @t18, 5, 4, @school_id),
('Kubernetes Ops', @class_do, @course_id, @t19, 5, 5, @school_id),
('Terraform IaC', @class_do, @course_id, @t20, 5, 4, @school_id),
('DevOps Culture', @class_do, @course_id, @t21, 5, 3, @school_id),
('AWS Cloud', @class_do, @course_id, @t22, 5, 4, @school_id),
('Serverless', @class_do, @course_id, @t23, 5, 4, @school_id),
('DORA Metrics', @class_do, @course_id, @t24, 5, 3, @school_id);

-- 7. Create Teachers and Subjects for AI & ML BTech
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Andrew Ng', @school_id); SET @t25 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Geoffrey Hinton', @school_id); SET @t26 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Yann LeCun', @school_id); SET @t27 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Yoshua Bengio', @school_id); SET @t28 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Fei-Fei Li', @school_id); SET @t29 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Demis Hassabis', @school_id); SET @t30 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Andrej Karpathy', @school_id); SET @t31 = LAST_INSERT_ID();
INSERT INTO `teacher` (`teacher_name`, `school_id`) VALUES ('Sam Altman', @school_id); SET @t32 = LAST_INSERT_ID();

INSERT INTO `subject` (`subject_name`, `class_id`, `course_id`, `teacher_id`, `semester`, `credits`, `school_id`) VALUES 
('Machine Learning', @class_ai, @course_id, @t25, 7, 5, @school_id),
('Deep Learning', @class_ai, @course_id, @t26, 7, 5, @school_id),
('Computer Vision', @class_ai, @course_id, @t27, 7, 4, @school_id),
('NLP Core', @class_ai, @course_id, @t28, 7, 4, @school_id),
('Image Processing', @class_ai, @course_id, @t29, 7, 4, @school_id),
('Reinforcement', @class_ai, @course_id, @t30, 7, 4, @school_id),
('Tesla Autopilot', @class_ai, @course_id, @t31, 7, 3, @school_id),
('Generative AI', @class_ai, @course_id, @t32, 7, 5, @school_id);

SET FOREIGN_KEY_CHECKS = 1;

-- Note: The password hash above matches 'test' using the standard pbkdf2 algorithm.
-- You can now login with username: test and password: test
