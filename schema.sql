-- Create the messages table
CREATE TABLE messages (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    session_id TEXT NOT NULL,
    role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
    content TEXT NOT NULL,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Index for faster retrieval by session
CREATE INDEX idx_messages_session_id ON messages (session_id);
CREATE INDEX idx_messages_created_at ON messages (created_at);

-- Create a view to get a list of sessions with their latest message preview
-- We use DISTINCT ON (session_id) to get the most recent message per session
CREATE VIEW session_previews AS
SELECT DISTINCT ON (session_id)
    session_id,
    content AS last_message,
    created_at AS last_updated
FROM messages
ORDER BY session_id, created_at DESC;
