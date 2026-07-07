## Agent Handoff Protocol (Jules)

### Merge Conflict Resolution

When Jules receives an `Agent Handoff` message with the workstream `Merge Conflict Resolution`, he must execute the following protocol:

1. **Check out the branch**: Pull the PR branch specified in the handoff message.
2. **Pull the target branch**: Pull the latest code from `main` (or the PR's base branch) to trigger the Git merge conflict markers locally.
3. **Analyze and Resolve**: Locate all `<<<<<<<` conflict markers. Analyze the context of the changes logically (e.g., combining independent additions, or choosing the correct logic if they collide) and remove the conflict markers, leaving the corrected code.
4. **Commit and Push**: Stage the resolved files, commit the merge, and push it back to the PR branch.
5. **Report**: Reply to the original PR comment confirming that the conflict has been resolved.
