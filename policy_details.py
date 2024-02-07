class PolicyDetails:
    def __init__(self, title, url, effective_date=None, issuance_date=None, responsible_office=None, subject_areas=[]):
        self.title = title
        self.filename = sanitize_filename(title)
        self.effective_date = effective_date
        self.issuance_date = issuance_date
        self.url = url
        self.responsible_office = responsible_office
        self.subject_areas = subject_areas

    def __str__(self):
        return f"{self.title} - {self.url} - {self.effective_date} - {self.issuance_date} - {self.responsible_office} - {self.subject_areas}"

def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', '', filename)