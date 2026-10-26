-- Synthetic bank catalog for a dedicated hosted PayLink project. No credentials.
INSERT INTO paylink.banks(routing_number,name) VALUES
 ('110000001','Meridian Bank'),('110000002','Northstar Credit Union'),('110000003','Pacific Trust')
ON CONFLICT(routing_number) DO NOTHING;
