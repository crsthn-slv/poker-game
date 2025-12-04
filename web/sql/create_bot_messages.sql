-- Create bot_messages table
CREATE TABLE IF NOT EXISTS bot_messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    action_type TEXT NOT NULL,
    message_text TEXT NOT NULL,
    lang_code TEXT DEFAULT 'pt-br',
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create index for faster lookups
CREATE INDEX IF NOT EXISTS idx_bot_messages_action_lang ON bot_messages(action_type, lang_code);

-- Insert initial data (10 variations per action)
INSERT INTO bot_messages (action_type, message_text, lang_code) VALUES
-- FOLD
('FOLD', 'Desisto dessa.', 'pt-br'),
('FOLD', 'Sem chance, estou fora.', 'pt-br'),
('FOLD', 'Essa mão não vai dar em nada. Fold.', 'pt-br'),
('FOLD', 'Melhor economizar minhas fichas.', 'pt-br'),
('FOLD', 'Passo. Boa sorte para quem fica.', 'pt-br'),
('FOLD', 'Não vou pagar para ver isso.', 'pt-br'),
('FOLD', 'Hoje não é meu dia. Fold.', 'pt-br'),
('FOLD', 'Lixo de mão. Desisto.', 'pt-br'),
('FOLD', 'Vocês que lutem. Estou fora.', 'pt-br'),
('FOLD', 'Fold. Próxima mão, por favor.', 'pt-br'),

-- CHECK
('CHECK', 'Mesa. Vamos ver a próxima carta.', 'pt-br'),
('CHECK', 'Check. Sua vez.', 'pt-br'),
('CHECK', 'Passo a vez.', 'pt-br'),
('CHECK', 'Nada a declarar. Check.', 'pt-br'),
('CHECK', 'Vamos com calma. Check.', 'pt-br'),
('CHECK', 'Check. Sem apostas por enquanto.', 'pt-br'),
('CHECK', 'Só observando. Check.', 'pt-br'),
('CHECK', 'Check. Mostre-me o que você tem.', 'pt-br'),
('CHECK', 'Tranquilo. Check.', 'pt-br'),
('CHECK', 'Check. O pote está bom assim.', 'pt-br'),

-- CALL
('CALL', 'Eu pago. Vamos ver.', 'pt-br'),
('CALL', 'Call. Estou curioso.', 'pt-br'),
('CALL', 'Pago pra ver.', 'pt-br'),
('CALL', 'Não vou a lugar nenhum. Call.', 'pt-br'),
('CALL', 'O preço é justo. Call.', 'pt-br'),
('CALL', 'Acompanho a aposta.', 'pt-br'),
('CALL', 'Call. Ainda estou no jogo.', 'pt-br'),
('CALL', 'Vamos ver o que acontece. Call.', 'pt-br'),
('CALL', 'Call. Não vou desistir fácil.', 'pt-br'),
('CALL', 'Aceito o desafio. Call.', 'pt-br'),

-- RAISE
('RAISE', 'Aumento a aposta!', 'pt-br'),
('RAISE', 'Vamos apimentar as coisas. Raise!', 'pt-br'),
('RAISE', 'Isso é pouco. Aumento!', 'pt-br'),
('RAISE', 'Tenho uma mão forte. Raise!', 'pt-br'),
('RAISE', 'Raise! Quem vai encarar?', 'pt-br'),
('RAISE', 'O pote merece mais fichas. Raise!', 'pt-br'),
('RAISE', 'Não vou deixar barato. Aumento!', 'pt-br'),
('RAISE', 'Raise. Vamos ver quem tem coragem.', 'pt-br'),
('RAISE', 'Estou confiante. Raise!', 'pt-br'),
('RAISE', 'Subindo a aposta!', 'pt-br'),

-- ALL-IN
('ALL-IN', 'Tudo ou nada! All-in!', 'pt-br'),
('ALL-IN', 'Empurro todas as minhas fichas. All-in!', 'pt-br'),
('ALL-IN', 'Chega de brincadeira. All-in!', 'pt-br'),
('ALL-IN', 'All-in! É agora ou nunca.', 'pt-br'),
('ALL-IN', 'Coloco minha vida na mesa. All-in!', 'pt-br'),
('ALL-IN', 'Não tenho medo. All-in!', 'pt-br'),
('ALL-IN', 'Todas as fichas no centro. All-in!', 'pt-br'),
('ALL-IN', 'Vou pro abraço. All-in!', 'pt-br'),
('ALL-IN', 'All-in. Paga pra ver?', 'pt-br'),
('ALL-IN', 'Momento da verdade. All-in!', 'pt-br'),

-- WIN (Winner)
('WIN', 'Sabia que ia ganhar essa!', 'pt-br'),
('WIN', 'As fichas vêm para o papai.', 'pt-br'),
('WIN', 'Vitória doce!', 'pt-br'),
('WIN', 'Essa foi fácil.', 'pt-br'),
('WIN', 'Obrigado pelas fichas!', 'pt-br'),
('WIN', 'Sorte? Não, habilidade.', 'pt-br'),
('WIN', 'Mais uma para a conta.', 'pt-br'),
('WIN', 'Quem é o mestre agora?', 'pt-br'),
('WIN', 'Bela tentativa, mas o pote é meu.', 'pt-br'),
('WIN', 'Ganhando e sorrindo.', 'pt-br'),

-- SHOW_CARDS (Showing cards at showdown)
('SHOW_CARDS', 'Olhem o que eu tinha.', 'pt-br'),
('SHOW_CARDS', 'Aqui estão minhas cartas.', 'pt-br'),
('SHOW_CARDS', 'Não foi dessa vez, mas olha o jogo.', 'pt-br'),
('SHOW_CARDS', 'Tinha esperança com isso aqui.', 'pt-br'),
('SHOW_CARDS', 'Mostrando o jogo.', 'pt-br'),
('SHOW_CARDS', 'Foi quase. Vejam.', 'pt-br'),
('SHOW_CARDS', 'Joguei com o que tinha.', 'pt-br'),
('SHOW_CARDS', 'Nada mal, né?', 'pt-br'),
('SHOW_CARDS', 'Revelando o mistério.', 'pt-br'),
('SHOW_CARDS', 'Minha mão era essa.', 'pt-br'),

-- MUCK (Giving up at end of round / Mucking)
('MUCK', 'Nem vou mostrar. Vergonha.', 'pt-br'),
('MUCK', 'Desisto. Fica pra próxima.', 'pt-br'),
('MUCK', 'Esquece, não mostro isso.', 'pt-br'),
('MUCK', 'Muck. Não vale a pena ver.', 'pt-br'),
('MUCK', 'Melhor esconder esse jogo.', 'pt-br'),
('MUCK', 'Passou perto, mas não mostro.', 'pt-br'),
('MUCK', 'Deixa quieto. Muck.', 'pt-br'),
('MUCK', 'Não mostro nem sob tortura.', 'pt-br'),
('MUCK', 'Vocês ganharam, não preciso humilhar.', 'pt-br'),
('MUCK', 'Muck. Segue o jogo.', 'pt-br');
