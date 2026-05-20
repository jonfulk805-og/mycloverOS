# CloverDesktop Templates

Custom desktop stack templates go here. Each directory is a desktop template containing a `docker-compose.yml` and optional `manifest.json`.

## Creating a Custom Template

```bash
mkdir /opt/cloverstack/modules/cloverdesktop/templates/my-desktop/
cd /opt/cloverstack/modules/cloverdesktop/templates/my-desktop/

# Create docker-compose.yml with your custom desktop stack
# Then start it with:
cloverdesktop start my-desktop
```

## Built-in templates are defined in the `cloverdesktop` CLI script.
## MCTVS Creator Market templates are stored in mctvs/installed/
