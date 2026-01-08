# DecisionEngine
# Determines whether decisions are allowed, restricted, or halted

class DecisionEngine:
    def decide(self, trust_state, hypothesis_state):
        if trust_state == "UNTRUSTED" or hypothesis_state == "INVALID":
            return "HALTED"

        if trust_state == "DEGRADED" or hypothesis_state == "WEAKENING":
            return "RESTRICTED"

        return "ALLOWED"
