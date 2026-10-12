create table if not exists public.legal_chunks (
  chunk_id text primary key,
  document_id text not null,
  file_name text,
  title text,
  law_number text,
  law_year integer,
  status text,
  effective_from text,
  effective_to text,
  article_number text,
  paragraph_number integer,
  clause_number integer,
  page_start integer,
  page_end integer,
  text text not null,
  created_at timestamptz not null default now()
);

create index if not exists legal_chunks_document_id_idx on public.legal_chunks (document_id);
create index if not exists legal_chunks_article_idx on public.legal_chunks (law_number, law_year, article_number);

-- The Streamlit server uses the service-role key server-side.
-- Do not expose that key in browser code or commit it to GitHub.
