-- 在 Supabase → SQL Editor 執行一次
create table if not exists submissions (
  id bigint generated always as identity primary key,
  exam_id text not null,
  grade int not null,
  subject text not null,
  year int not null,
  class text not null,
  seat int not null,
  name text,
  answers int[] not null,   -- 0 = 未作答
  score int not null,
  total int not null,
  client_id text unique,   -- 前端產生，重送時不會重複寫入
  created_at timestamptz default now()
);
create index if not exists submissions_exam_idx on submissions (exam_id, class);
-- 已建過表的人補跑：alter table submissions add column if not exists client_id text unique;
alter table submissions enable row level security;
-- 學生（anon）只能新增，不能讀
create policy "anon insert" on submissions for insert to anon with check (true);

create table if not exists teacher_config (pw text not null);
alter table teacher_config enable row level security;  -- 無 policy = anon 完全讀不到
insert into teacher_config values ('請改成你的教師密碼');

create or replace function teacher_get_submissions(pw text)
returns setof submissions language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from teacher_config t where t.pw = teacher_get_submissions.pw) then
    raise exception 'unauthorized';
  end if;
  return query select * from submissions order by created_at desc;
end $$;

create or replace function teacher_delete_submission(pw text, sid bigint)
returns void language plpgsql security definer set search_path = public as $$
begin
  if not exists (select 1 from teacher_config t where t.pw = teacher_delete_submission.pw) then
    raise exception 'unauthorized';
  end if;
  delete from submissions where id = sid;
end $$;

grant execute on function teacher_get_submissions(text), teacher_delete_submission(text, bigint) to anon;
