import json
import db
from datetime import datetime

def import_jobs_from_json(json_file_path, recruiter_id):
    """Import jobs from JSON file to database"""
    try:
        with open(json_file_path, 'r', encoding='utf-8') as f:
            companies_data = json.load(f)

        for company_data in companies_data:
            # Add company (will return existing id if already exists)
            company_id = db.add_company(
                name=company_data['company'],
                url=company_data.get('url'),
                remote_friendly=company_data.get('remoteFriendly', False),
                market=company_data.get('market'),
                size=company_data.get('size')
            )

            if company_id:
                print(f"Processing company: {company_data['company']}")

                # Add jobs for this company
                for job_data in company_data.get('jobs', []):
                    # Parse salary range
                    salary_range = job_data.get('salaryRange', {})
                    salary_from = salary_range.get('from')
                    salary_to = salary_range.get('to')
                    salary_currency = salary_range.get('currency', 'USD')

                    # Parse equity
                    equity = job_data.get('equity', {})
                    equity_from = equity.get('from', 0)
                    equity_to = equity.get('to', 0)

                    # Parse posted date
                    posted_date = None
                    if job_data.get('posted'):
                        try:
                            posted_date = datetime.strptime(job_data['posted'], '%Y-%m-%d').date()
                        except ValueError:
                            print(f"Invalid date format for job {job_data.get('title')}: {job_data['posted']}")

                    # Add job
                    db.add_job(
                        company_id=company_id,
                        recruiter_id=recruiter_id,
                        position=job_data.get('position', ''),
                        title=job_data.get('title', ''),
                        description=job_data.get('description', ''),
                        url=job_data.get('url'),
                        job_type=job_data.get('type', 'full-time'),
                        posted=posted_date,
                        location=job_data.get('location', 'Remote'),
                        skills=job_data.get('skills', []),
                        salary_from=salary_from,
                        salary_to=salary_to,
                        salary_currency=salary_currency,
                        equity_from=equity_from,
                        equity_to=equity_to,
                        perks=job_data.get('perks', []),
                        apply_url=job_data.get('apply')
                    )
                    print(f"Added job: {job_data.get('title')} at {company_data['company']}")
            else:
                print(f"Failed to get company ID for {company_data['company']}")

        print("Import completed successfully!")

    except Exception as e:
        print(f"Error importing jobs: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Create tables first
    db.create_tables()

    # Get the first recruiter to assign jobs to
    recruiters = db.get_all_recruiters()
    if not recruiters:
        print("No recruiters found. Please create a recruiter first.")
        exit(1)

    default_recruiter_id = recruiters[0]['id']
    print(f"Assigning jobs to recruiter: {recruiters[0]['username']} (ID: {default_recruiter_id})")

    # Clear existing jobs to avoid duplicates
    conn = db.get_db_connection()
    cur = conn.cursor()
    cur.execute("DELETE FROM jobs")
    conn.commit()
    cur.close()
    conn.close()
    print("Cleared existing jobs")

    # Import jobs
    import_jobs_from_json('jobs.json', default_recruiter_id)