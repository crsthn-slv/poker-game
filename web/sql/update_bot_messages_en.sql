-- Clear existing messages (since user wants English)
DELETE FROM bot_messages;

-- Insert English data (10 variations per action)
INSERT INTO bot_messages (action_type, message_text, lang_code) VALUES
-- FOLD
('FOLD', 'I fold.', 'en-us'),
('FOLD', 'Too rich for my blood.', 'en-us'),
('FOLD', 'Folding this trash.', 'en-us'),
('FOLD', 'I''m out.', 'en-us'),
('FOLD', 'Pass.', 'en-us'),
('FOLD', 'Not this time.', 'en-us'),
('FOLD', 'Fold.', 'en-us'),
('FOLD', 'Saving my chips.', 'en-us'),
('FOLD', 'You win this one.', 'en-us'),
('FOLD', 'Giving up.', 'en-us'),

-- CHECK
('CHECK', 'Check.', 'en-us'),
('CHECK', 'Checking.', 'en-us'),
('CHECK', 'I check.', 'en-us'),
('CHECK', 'Pass to you.', 'en-us'),
('CHECK', 'Let''s see the next card.', 'en-us'),
('CHECK', 'No bets from me.', 'en-us'),
('CHECK', 'Check, your turn.', 'en-us'),
('CHECK', 'Staying in, check.', 'en-us'),
('CHECK', 'Quiet round. Check.', 'en-us'),
('CHECK', 'Check.', 'en-us'),

-- CALL
('CALL', 'I call.', 'en-us'),
('CALL', 'Calling.', 'en-us'),
('CALL', 'I''m in.', 'en-us'),
('CALL', 'Let''s see it.', 'en-us'),
('CALL', 'Call.', 'en-us'),
('CALL', 'Matching the bet.', 'en-us'),
('CALL', 'I''ll pay to see.', 'en-us'),
('CALL', 'Call, let''s go.', 'en-us'),
('CALL', 'Not folding yet. Call.', 'en-us'),
('CALL', 'Price is right. Call.', 'en-us'),

-- RAISE
('RAISE', 'Raise!', 'en-us'),
('RAISE', 'Raising the stakes.', 'en-us'),
('RAISE', 'I raise.', 'en-us'),
('RAISE', 'Let''s make it interesting. Raise.', 'en-us'),
('RAISE', 'Bump it up.', 'en-us'),
('RAISE', 'Raise.', 'en-us'),
('RAISE', 'Too cheap. Raise.', 'en-us'),
('RAISE', 'I have a good feeling. Raise.', 'en-us'),
('RAISE', 'Adding more chips. Raise.', 'en-us'),
('RAISE', 'Raise! Who''s with me?', 'en-us'),

-- ALL-IN
('ALL-IN', 'All-in!', 'en-us'),
('ALL-IN', 'Pushing it all.', 'en-us'),
('ALL-IN', 'All chips in.', 'en-us'),
('ALL-IN', 'Do or die. All-in.', 'en-us'),
('ALL-IN', 'I''m all-in.', 'en-us'),
('ALL-IN', 'Everything I have.', 'en-us'),
('ALL-IN', 'All-in. Good luck.', 'en-us'),
('ALL-IN', 'No turning back. All-in.', 'en-us'),
('ALL-IN', 'Maximum risk. All-in.', 'en-us'),
('ALL-IN', 'All-in!', 'en-us'),

-- WIN (Winner)
('WIN', 'I knew I had it!', 'en-us'),
('WIN', 'Chips coming to papa.', 'en-us'),
('WIN', 'Nice pot.', 'en-us'),
('WIN', 'Easy money.', 'en-us'),
('WIN', 'Thanks for the chips!', 'en-us'),
('WIN', 'Better luck next time.', 'en-us'),
('WIN', 'Winner winner!', 'en-us'),
('WIN', 'Read you like a book.', 'en-us'),
('WIN', 'My pot.', 'en-us'),
('WIN', 'Great hand!', 'en-us'),

-- SHOW_CARDS (Showing cards at showdown)
('SHOW_CARDS', 'Look at what I had.', 'en-us'),
('SHOW_CARDS', 'Showing my hand.', 'en-us'),
('SHOW_CARDS', 'Close one, look.', 'en-us'),
('SHOW_CARDS', 'Had some potential.', 'en-us'),
('SHOW_CARDS', 'Here are my cards.', 'en-us'),
('SHOW_CARDS', 'Just missed it.', 'en-us'),
('SHOW_CARDS', 'Playing these.', 'en-us'),
('SHOW_CARDS', 'Not enough, I guess.', 'en-us'),
('SHOW_CARDS', 'My cards.', 'en-us'),
('SHOW_CARDS', 'Revealing.', 'en-us'),

-- MUCK (Giving up at end of round / Mucking)
('MUCK', 'Mucking.', 'en-us'),
('MUCK', 'Not showing this.', 'en-us'),
('MUCK', 'You don''t need to see.', 'en-us'),
('MUCK', 'Muck.', 'en-us'),
('MUCK', 'Hiding my shame.', 'en-us'),
('MUCK', 'Better luck next time.', 'en-us'),
('MUCK', 'Folded face down.', 'en-us'),
('MUCK', 'Secret.', 'en-us'),
('MUCK', 'Nope, not showing.', 'en-us'),
('MUCK', 'Muck.', 'en-us');
