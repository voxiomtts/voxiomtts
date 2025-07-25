# Updated endpoint for voxiomtts/voxiomtts
UPDATE_URL = "https://api.github.com/repos/voxiomtts/voxiomtts/releases/latest"

class UpdateChecker(QThread):
    def get_latest_info(self):
        response = requests.get(
            UPDATE_URL,
            headers={"Accept": "application/vnd.github.v3+json"},
            timeout=5
        )
        return response.json()
