-- questionsテーブル
CREATE TABLE IF NOT EXISTS questions (
    id SERIAL PRIMARY KEY,
    question_text TEXT NOT NULL,
    choice_a TEXT NOT NULL,
    choice_b TEXT NOT NULL,
    choice_c TEXT NOT NULL,
    choice_d TEXT NOT NULL,
    correct_answer CHAR(1) NOT NULL CHECK (correct_answer IN ('1', '2', '3', '4')),
    start_time TIMESTAMP
);

-- answersテーブル
CREATE TABLE IF NOT EXISTS answers (
    id SERIAL PRIMARY KEY,
    username TEXT NOT NULL,
    question_id INT NOT NULL REFERENCES questions(id),
    answer CHAR(1) NOT NULL CHECK (answer IN ('1', '2', '3', '4')),
    is_correct BOOLEAN NOT NULL,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- user_answersテーブル
CREATE TABLE IF NOT EXISTS user_answers (
    id SERIAL PRIMARY KEY,
    user_name VARCHAR(50) NOT NULL,
    question_id INT NOT NULL,
    selected_choice VARCHAR(1) NOT NULL,
    is_correct BOOLEAN NOT NULL,
    answered_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    answer_time_ms INT,
    FOREIGN KEY (question_id) REFERENCES questions(id)
);

-- 初期データ投入（例）
INSERT INTO questions (question_text, choice_a, choice_b, choice_c, choice_d, correct_answer)
VALUES
('Pythonのバージョン3.11は何年にリリースされた？', '2022年', '2023年', '2024年', '2025年', '1'),
('Pythonのバージョン3.13は何年にリリースされた？', '2022年', '2023年', '2024年', '2025年', '3');

INSERT INTO user_answers (user_name, question_id, selected_choice, is_correct, answer_time_ms)
VALUES
('ー', 1, '1', 't', 99988),
('ーー', 1, '1', 't', 99989),
('ーーー', 1, '1', 't', 99990),
('ーーーー', 1, '1', 't', 99991),
('ーーーーー', 1, '1', 't', 99992),
('ーーーーーー', 1, '1', 't', 99993),
('ーーーーーーー', 1, '1', 't', 99994),
('ーーーーーーーー', 1, '1', 't', 99995),
('ーーーーーーーーー', 1, '1', 't', 99996),
('ーーーーーーーーーー', 1, '1', 't', 99997),
('ーーーーーーーーーーー', 1, '1', 't', 99998),
('ーーーーーーーーーーーー', 1, '1', 't', 99999);
