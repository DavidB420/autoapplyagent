from ..models import Job

class JobEvaluator:
    def score(self, job: Job) -> int:
        text = f"{job.title} {job.description or ''}".lower()
        score = 0
        for keyword, points in {
            "software": 20, "developer": 20, "engineer": 20,
            "machine learning": 25, "ai": 15, "data": 10,
            "python": 10, "cloud": 10,
        }.items():
            if keyword in text:
                score += points
        return min(score, 100)
