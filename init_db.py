from app import app, init_or_upgrade_db, create_default_users

with app.app_context():
    init_or_upgrade_db()
    create_default_users()
    print("[OK] ApplyMate Database Ready & Upgraded.")
    print("Admin       -> admin@applymate.com / Admin@123")
    print("Assigner    -> assigner@applymate.com / Assigner@123")
    print("S1 Employee -> s1@applymate.com / S1@123 (Alex - Job Finder)")
    print("S1 Employee -> s1_lisa@applymate.com / S1@123 (Lisa - Job Finder)")
    print("S2 Employee -> s2@applymate.com / S2@123 (Sarah - ATS Resume Maker)")
    print("S2 Employee -> s2_david@applymate.com / S2@123 (David - ATS Resume Maker)")
    print("S3 Employee -> s3@applymate.com / S3@123 (Sam - Job Applier)")
    print("S3 Employee -> s3_elena@applymate.com / S3@123 (Elena - Job Applier)")