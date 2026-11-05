# `fpptools config`

Shows the FP Pro configuration fpptools will use, without changing anything. **Run it first** when a command says a folder or the database can't be found.

```powershell
fpptools config
```

```
INI             C:\Users\<you>\AppData\Roaming\Emmegisoft\FP_PRO\FP_PRO.INI
Configuration   COLOMBIA_ALUMINA_MM
STR_PATH        D:\CONFIGS11\COLOMBIA_ALUMINA_MM\STR\
BLK_PATH        D:\CONFIGS11\COLOMBIA_ALUMINA_MM\BLK\
JOB_PATH        D:\CONFIGS11\COLOMBIA_ALUMINA_MM\JOB\
CONFIGS_PATH    C:\FP_PRO\CONFIGS\
Database        MySQL localhost:3307/fp_pro32_colombia_alumina_mm (user …, charset latin1)
```

| Line | From FP_PRO.INI |
|---|---|
| INI | the file read: `%APPDATA%\Emmegisoft\FP_PRO\FP_PRO.INI`, or `--ini` / `FPPTOOLS_INI` |
| Configuration | `[GENERAL] CURRENT_CONFIGURATION` |
| STR_PATH, BLK_PATH, JOB_PATH, CONFIGS_PATH | `[SYSTEM]`; `[not found]` after a folder that doesn't exist |
| Database | `[SYSTEM] CONN_STR_FP_PRO`: `1` MySQL (`[MYSQL]` DB_SERVER_NAME, DB_PORT, DB_NAME, DB_USER, DB_CHARSET; port 3306 and charset latin1 when missing), `0` Access (`Fp_Pro32.MDB` in `MDB_PATH`) |

The password is never shown or written anywhere.

To work on another configuration, switch it in FP Pro, or point fpptools at another INI: `fpptools --ini D:\otro\FP_PRO.INI config`.
