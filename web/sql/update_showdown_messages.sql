-- Update Showdown Messages with Placeholders

-- 1. Remove existing generic SHOW_CARDS messages to avoid mixing styles
DELETE FROM bot_messages WHERE action_type = 'SHOW_CARDS';

-- 2. Insert new messages with placeholders {cards} and {hand_name}
INSERT INTO bot_messages (action_type, message_text, lang_code) VALUES
-- PT-BR
('SHOW_CARDS', 'Tenho {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Olha meu {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', '{hand_name}! {cards}', 'pt-br'),
('SHOW_CARDS', 'Aqui está: {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Não deu pra mim, só {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Segura esse {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Minha mão: {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Tentei blefar com {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Nada mal: {hand_name} {cards}', 'pt-br'),
('SHOW_CARDS', 'Vejam: {hand_name} {cards}', 'pt-br'),

-- EN-US
('SHOW_CARDS', 'I have {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'Look at my {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', '{hand_name}! {cards}', 'en-us'),
('SHOW_CARDS', 'Here it is: {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'Not enough, just {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'Check this {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'My hand: {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'Tried to bluff with {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'Not bad: {hand_name} {cards}', 'en-us'),
('SHOW_CARDS', 'See: {hand_name} {cards}', 'en-us');
