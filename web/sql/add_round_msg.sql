-- Add MSG_ROUND translation
INSERT INTO localizations (key, lang_code, content) VALUES
('MSG_ROUND', 'pt-br', 'Rodada'),
('MSG_ROUND', 'en-us', 'Round')
ON CONFLICT (key, lang_code) DO UPDATE SET content = EXCLUDED.content;
