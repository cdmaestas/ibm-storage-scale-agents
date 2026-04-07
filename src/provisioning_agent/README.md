# Provisioning Agent — Tools & Prompts Reference

This document describes the tools supported by the **Scale Provisioning Agent** and provides example prompts you can use in the interactive CLI.


## Supported Tools

Tools are divided into two categories based on whether they require explicit human confirmation before execution.

### Tools Requiring Confirmation

These tools make **write** or **destructive** changes to the cluster. The agent will pause and ask for your approval before proceeding.

| Tool | Description |
|------|-------------|
| `create_independent_fileset` | Create an independent fileset with its own inode space (supports snapshots) |
| `create_dependent_fileset` | Create a dependent fileset that shares the parent's inode space (more efficient, no independent snapshots) |
| `delete_fileset` | Delete a fileset from a filesystem |
| `create_fileset_snapshot` | Create a snapshot for an independent fileset |
| `delete_fileset_snapshot` | Delete a fileset snapshot |

### Tools Without Confirmation

These tools perform **read-only** or **non-destructive** operations and execute immediately.

| Tool | Description |
|------|-------------|
| `list_filesets` | List all filesets in a filesystem |
| `link_fileset` | Link a fileset to a junction path |
| `unlink_fileset` | Unlink a fileset from its junction path |
| `list_fileset_snapshots` | List all snapshots for a fileset |


## Tool Parameters

### `create_independent_fileset` / `create_dependent_fileset`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name (e.g. `fs1`) |
| `fileset_data` | Yes | JSON object with at minimum `{"name": "fileset_name"}`. Optional fields: `path`, `owner`, `permissions`, `comment` |
| `domain` | No | Domain for authorization. Omit to use the default domain |

### `list_filesets`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `domain` | No | Domain for authorization |

### `delete_fileset`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset_name` | Yes | Name of the fileset to delete |

### `link_fileset`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset_name` | Yes | Name of the fileset to link |
| `link_data` | Yes | JSON object with junction path (e.g. `{"path": "/gpfs/fs1/myfset"}`) |
| `domain` | No | Domain for authorization |

### `unlink_fileset`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset_name` | Yes | Name of the fileset to unlink |
| `unlink_data` | No | JSON object (e.g. `{"force": true}`) |
| `domain` | No | Domain for authorization |

### `create_fileset_snapshot`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset` | Yes | Name of an **independent** fileset |
| `snapshot_data` | Yes | JSON object with snapshot name (e.g. `{"name": "snap1"}`) |
| `domain` | No | Domain for authorization |

### `list_fileset_snapshots`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset` | Yes | Fileset name |
| `domain` | No | Domain for authorization |

### `delete_fileset_snapshot`

| Parameter | Required | Description |
|-----------|----------|-------------|
| `filesystem` | Yes | Filesystem name |
| `fileset` | Yes | Fileset name |
| `snapshot_name` | Yes | Name of the snapshot to delete |
| `domain` | No | Domain for authorization |


## Example Prompts

### Fileset Listing

```
List me all filesets from filesystem fs1
```

```
Show filesets in fs1
```

```
List filesets from fs1, fs2
```

### Fileset Creation

```
Create an independent fileset named myfset in filesystem fs1
```

```
Create independent filesets named fset1, fset2 in filesystem fs1
```

```
Create a dependent fileset called logs in fs1 with path /gpfs/fs1/logs
```

> **Note:** If you do not specify the fileset type (independent or dependent), the agent will ask you to choose before proceeding.
> Comma-separated names are supported — the agent will execute the operation for each item in sequence.

### Fileset Linking / Unlinking

```
Link fileset myfset in fs1 to junction path /gpfs/fs1/myfset
```

```
Unlink fileset myfset from fs1
```

### Fileset Deletion

```
Delete fileset myfset from filesystem fs1
```

### Snapshot Operations

```
List snapshots for fileset myfset in fs1
```

```
Create a snapshot named snap1 for fileset myfset in fs1
```

```
Delete snapshot snap1 from fileset myfset in filesystem fs1
```


## Agent Behavior Notes

- The `domain` parameter is **optional** for all tools. Do not provide it unless your environment requires a specific domain — the system uses the default domain automatically.
- Confirmation-required tools will display the operation details and wait for your `yes`/`no` approval before executing.
- Snapshots can only be created on **independent** filesets (those with their own inode space).
- Tool results are logged to the configured log file at `DEBUG` level. Set `level = DEBUG` in [`config/agents_settings.ini`](../../config/agents_settings.ini) to capture full tool output.
