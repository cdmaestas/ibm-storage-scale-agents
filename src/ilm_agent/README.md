# ILM Agent — Tools & Prompts Reference

This document describes the tools supported by the **Scale ILM (Information Lifecycle Management) Agent** and provides example prompts you can use in the interactive CLI.

## Supported Tools

Tools are divided into two categories based on whether they require explicit human confirmation before execution.

### Tools Requiring Confirmation

These tools make **write** or **policy-changing** operations to the cluster. The agent will pause and ask for your approval before proceeding.

| Tool | Description |
|------|-------------|
| `update_policy` | Update a storage policy for a filesystem with new ILM rules |
| `apply_policy` | Execute mmapplypolicy to run the ILM policy on a filesystem |

### Tools Without Confirmation

These tools perform **read-only** or **validation** operations and execute immediately.

| Tool | Description |
|------|-------------|
| `get_policy` | Retrieve the current storage policy for a filesystem |
| `list_storage_pools` | List all storage pools in a filesystem |
| `test_policy` | Test/validate a storage policy without applying it |

## Tool Parameters

### `get_policy`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name (e.g. `fs1`) |
| `domain` | No | Domain for authorization. Omit to use the default domain |

### `list_storage_pools`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `domain` | No | Domain for authorization |

### `test_policy`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name to test the policy against |
| `policy_contents` | Yes | Plain-text IBM Storage Scale RULE statements. The agent will automatically base64-encode the content |
| `domain` | No | Domain for authorization |

### `update_policy`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name to apply the policy to |
| `policy_contents` | Yes | Plain-text IBM Storage Scale RULE statements. The agent will automatically base64-encode the content |
| `domain` | No | Domain for authorization |

### `apply_policy`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name to run the policy on |
| `domain` | No | Domain for authorization |


## ILM Policy Workflow

The ILM Agent uses a **custom workflow graph** that enforces proper sequencing of policy operations:

1. **Get Policy** → Retrieve current policy (optional, for reference)
2. **List Storage Pools** → View available storage pools (optional, for planning)
3. **Test Policy** → Validate policy syntax and logic
4. **Update Policy** → Write the policy to filesystem metadata (requires confirmation)
5. **Apply Policy** → Execute the policy engine to scan and migrate files (requires confirmation, runs automatically after update by default)

The workflow automatically:
- Validates policy syntax using IBM Storage Scale rules
- Checks for redundant rules
- Preserves existing policy rules when updating
- Applies the policy after updating (unless explicitly skipped)
- Provides clear status messages at each step


## Example Prompts

### Viewing Current Policy

```
Show me the current ILM policy for filesystem fs1
```

```
Get the policy from fs1
```

```
What is the current policy for fs1?
```

### Listing Storage Pools

```
List storage pools in filesystem fs1
```

```
Show me all pools in fs1
```

```
What storage pools are available in fs1?
```

### Testing a Policy

```
Test this policy for fs1: migrate files older than 30 days from system pool to archive pool
```

```
Validate a policy that deletes files not accessed in 180 days from fs1
```

### Updating a Policy

**Note**: By default, updating a policy will also apply it automatically. If you only want to update without applying, use phrases like "only update" or "just update" in your prompt.

```
Update the policy for fs1 to migrate files older than 90 days to the archive pool
```

```
Add a rule to fs1 policy: delete log files older than 365 days
```

```
Modify the policy for fs1 to move files larger than 1GB to cold storage
```

**To update without applying:**

```
Only update the policy for fs1 to migrate files older than 90 days (don't apply)
```

### Complete Workflow (Create, Update, and Apply)

```
For filesystem fs1, create and apply a policy to migrate files older than 60 days from system pool to archive pool
```

The agent will:
1. Retrieve existing policy to preserve current rules
2. Verify storage pools exist
3. Generate the new rule using LLM with correct IBM Storage Scale syntax
4. Test the policy syntax
5. Ask for confirmation to update the policy
6. Update the policy in filesystem metadata
7. Automatically proceed to apply the policy (asks for confirmation)
8. Execute mmapplypolicy to scan and migrate files


## Policy Syntax Auto-Correction

The ILM Agent automatically corrects common LLM-generated syntax mistakes:

| Common Mistake | Auto-Corrected To |
|----------------|-------------------|
| `RULE "name"` | `RULE name` (removes quotes) |
| `FROM POOL "system"` | `FROM POOL 'system'` (double → single quotes) |
| `NAME LIKE "%.log"` | `NAME LIKE '%.log'` (double → single quotes) |
| `DAYS(CURRENT_TIMESTAMP - ACCESS_TIME)` | `DAYS(CURRENT_TIMESTAMP) - DAYS(ACCESS_TIME)` |


## Related Documentation

- [IBM Storage Scale Documentation](https://www.ibm.com/docs/en/storage-scale) - Official policy syntax reference
