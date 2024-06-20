import re


class PolicyDetails:
    """
    Represents the details of a policy. Will be used as common metadata for all policies
    """

    def __init__(
        self,
        title="",
        url="",
        effective_date=None,
        issuance_date=None,
        responsible_office=None,
        subject_areas=[],
        keywords=[],
        classifications=[],
    ):
        self.title = title
        self.filename = sanitize_filename(title)
        self.effective_date = effective_date
        self.issuance_date = issuance_date
        self.url = url
        self.responsible_office = responsible_office
        self.keywords = keywords
        self.classifications = classifications
        self.subject_areas = subject_areas

    def to_vectorized_document(self, text: str):
        return VectorDocument(text, Metadata(**self.__dict__))

    def __str__(self):
        return f"{self.title} - {self.url} - {self.effective_date} - {self.issuance_date} - {self.responsible_office} - {self.subject_areas} - {self.keywords} - {self.classifications}"


def sanitize_filename(filename):
    """Sanitize the filename by removing or replacing invalid characters."""
    return re.sub(r'[\\/*?:"<>|]', "", filename)


class VectorDocument:
    def __init__(self, text, metadata):
        self.text = text
        self.metadata = Metadata(**metadata)

    def __str__(self):
        return f"{self.text} - {self.metadata}"


class Metadata:
    def __init__(
        self,
        title,
        filename,
        url,
        hash="",
        content_length=0,
        scope="",
        start_index=0,
        effective_date=None,
        issuance_date=None,
        responsible_office=None,
        subject_areas=[],
        keywords=[],
        classifications=[],
    ):
        self.title = title
        self.filename = filename
        self.effective_date = effective_date
        self.issuance_date = issuance_date
        self.url = url
        self.responsible_office = responsible_office
        self.keywords = keywords
        self.classifications = classifications
        self.subject_areas = subject_areas
        self.hash = hash
        self.content_length = content_length
        self.scope = scope
        self.start_index = start_index

    def __str__(self):
        return f"{self.title} - {self.filename} - {self.effective_date} - {self.issuance_date} - {self.url} - {self.responsible_office} - {self.keywords} - {self.classifications} - {self.subject_areas} - {self.hash} - {self.content_length} - {self.scope} - {self.start_index}"
