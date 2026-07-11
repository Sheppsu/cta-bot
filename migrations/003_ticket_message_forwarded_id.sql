ALTER TABLE IF EXISTS public.ticket_message
    ADD COLUMN forwarded_message_id bigint;
