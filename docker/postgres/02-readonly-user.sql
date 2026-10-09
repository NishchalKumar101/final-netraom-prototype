-- Classroom read-only login (Adminer: user student / password student)
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'student') THEN
    CREATE ROLE student LOGIN PASSWORD 'student';
  END IF;
END
$$;

GRANT CONNECT ON DATABASE cspm_demo TO student;
GRANT USAGE ON SCHEMA public TO student;
GRANT SELECT ON ALL TABLES IN SCHEMA public TO student;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO student;
