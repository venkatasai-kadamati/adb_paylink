# Supabase database trust certificate

`supabase-ca.crt` is the public Supabase Root 2021 CA, downloaded from the certificate link in the project's Database Settings:
https://supabase-downloads.s3-ap-southeast-1.amazonaws.com/prod/ssl/prod-ca-2021.crt

It is public trust material, not a credential. Hosted connections use `sslmode=verify-full` and this certificate as `sslrootcert`. In the Render container the path is `/app/backend/certs/supabase-ca.crt`. Do not bypass certificate verification.
