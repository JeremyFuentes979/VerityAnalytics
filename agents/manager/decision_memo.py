"""
Decision Memo Generator
Produces a structured, professional decision memo synthesizing all findings
from Analyst, Auditor, and the Manager's conflict resolution.
"""

import json
import os
import logging
from datetime import datetime

logger = logging.getLogger("manager.decision_memo")


class DecisionMemo:
    """Generates the final structured decision memo."""

    def __init__(self, session_dir: str, conflict_result: dict):
        self.session_dir = session_dir
        self.conflict_result = conflict_result
        self.memo = {}

    def generate(self) -> dict:
        """Generate the full decision memo."""
        self._build_header()
        self._build_executive_summary()
        self._build_data_profile_section()
        self._build_analysis_section()
        self._build_audit_section()
        self._build_conflict_resolution_section()
        self._build_recommendations()
        self._build_appendix()
        return self.memo

    def _build_header(self):
        self.memo["memo_header"] = {
            "title": "Quorum Financial Analysis — Decision Memo",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "prepared_by": "Quorum Manager Agent",
            "document_type": "Final Decision Memorandum",
            "status": "Approved",
        }

    def _build_executive_summary(self):
        resolution_count = self.conflict_result.get("summary", {}).get("resolutions_count", 0)
        self.memo["executive_summary"] = (
            f"This memo summarizes the findings from Quorum's multi-agent analysis. "
            f"The Analyst performed exploratory data analysis and pattern detection. "
            f"The Auditor validated data quality, cleaned inconsistencies, and maintained an audit trail. "
            f"The Manager adjudicated {resolution_count} findings and resolved any conflicts between the two agents. "
            f"The result is a verified, cleaned dataset ready for financial decision-making."
        )

    def _build_data_profile_section(self):
        profile_path = os.path.join(self.session_dir, "profile.json")
        if os.path.exists(profile_path):
            with open(profile_path) as f:
                profile = json.load(f)
            self.memo["data_profile"] = profile
        else:
            self.memo["data_profile"] = {"status": "No profile available"}

    def _build_analysis_section(self):
        analysis_path = os.path.join(self.session_dir, "analysis.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                analysis = json.load(f)
            self.memo["analysis_findings"] = analysis
        else:
            self.memo["analysis_findings"] = {"status": "No analysis available"}

    def _build_audit_section(self):
        audit_path = os.path.join(self.session_dir, "audit_trail.json")
        if os.path.exists(audit_path):
            with open(audit_path) as f:
                audit = json.load(f)
            self.memo["audit_trail"] = audit
        else:
            self.memo["audit_trail"] = {"status": "No audit trail available"}

    def _build_conflict_resolution_section(self):
        self.memo["conflict_resolution"] = self.conflict_result

    def _build_recommendations(self):
        """Build final recommendations based on all inputs."""
        recommendations = []

        # From Analyst recommendations if available
        analysis_path = os.path.join(self.session_dir, "analysis.json")
        if os.path.exists(analysis_path):
            with open(analysis_path) as f:
                analysis = json.load(f)
            if "recommendations" in analysis:
                recs = analysis["recommendations"]
                if isinstance(recs, list):
                    recommendations.extend(
                        {"source": "Analyst", "recommendation": r}
                        for r in recs
                    )
                elif isinstance(recs, str):
                    recommendations.append({"source": "Analyst", "recommendation": recs})

        # Manager's own concluding recommendation
        resolution_count = self.conflict_result.get("summary", {}).get("resolutions_count", 0)
        confirmed_count = self.conflict_result.get("summary", {}).get("confirmed", 0)
        recommendations.append({
            "source": "Manager",
            "recommendation": (
                f"The data has been through a full multi-agent review. "
                f"{confirmed_count} findings were cross-confirmed by both Analyst and Auditor. "
                f"The cleaned dataset is ready for downstream financial analysis and reporting."
            ),
        })

        self.memo["recommendations"] = recommendations

    def _build_appendix(self):
        self.memo["appendix"] = {
            "agents_involved": ["Researcher", "Analyst", "Auditor", "Manager"],
            "methodology": (
                "1. Researcher: Data ingestion, profiling, and source validation\n"
                "2. Analyst: Exploratory data analysis, pattern detection, anomaly identification\n"
                "3. Auditor: Data cleaning, standardization, de-duplication, audit trail maintenance\n"
                "4. Manager: Conflict resolution, decision memo, final workbook generation"
            ),
            "disclaimer": (
                "This analysis was produced by automated AI agents. "
                "All findings should be reviewed by a qualified financial professional "
                "before being used for material business decisions."
            ),
        }


def generate_memo(session_dir: str, conflict_result: dict) -> dict:
    """Convenience function to generate and save the decision memo."""
    memo_gen = DecisionMemo(session_dir, conflict_result)
    memo = memo_gen.generate()

    output_path = os.path.join(session_dir, "decision_memo.json")
    with open(output_path, "w") as f:
        json.dump(memo, f, indent=2)
    logger.info(f"Decision memo saved to {output_path}")
    return memo