CREATE TABLE IF NOT EXISTS public.guild_data
(
    guild_id bigint NOT NULL,
    message_id bigint NOT NULL,
    CONSTRAINT guild_data_pkey PRIMARY KEY (guild_id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.guild_data
    OWNER to postgres;

CREATE TABLE IF NOT EXISTS public.ticket
(
    creator_id bigint NOT NULL,
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    is_open boolean NOT NULL,
    channel_id bigint,
    is_dm boolean NOT NULL,
    close_message_id bigint,
    open_message_id bigint,
    is_deleted boolean NOT NULL,
    CONSTRAINT transcript_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.ticket
    OWNER to postgres;

CREATE TABLE IF NOT EXISTS public.ticket
(
    creator_id bigint NOT NULL,
    id bigint NOT NULL GENERATED ALWAYS AS IDENTITY ( INCREMENT 1 START 1 MINVALUE 1 MAXVALUE 9223372036854775807 CACHE 1 ),
    is_open boolean NOT NULL,
    channel_id bigint,
    is_dm boolean NOT NULL,
    close_message_id bigint,
    open_message_id bigint,
    is_deleted boolean,
    CONSTRAINT transcript_pkey PRIMARY KEY (id)
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.ticket
    OWNER to postgres;

CREATE TABLE IF NOT EXISTS public.ticket_message_attachment
(
    ticket_message_id bigint NOT NULL,
    attachment_url text COLLATE pg_catalog."default" NOT NULL,
    CONSTRAINT ticket_message_attachment_fkey FOREIGN KEY (ticket_message_id)
        REFERENCES public.ticket_message (id) MATCH SIMPLE
        ON UPDATE NO ACTION
        ON DELETE NO ACTION
)
TABLESPACE pg_default;
ALTER TABLE IF EXISTS public.ticket_message_attachment
    OWNER to postgres;