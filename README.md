# upsint

[![Codacy Badge](https://api.codacy.com/project/badge/Grade/7c4e622a12074303b4b8752f87ef0c80)](https://www.codacy.com/app/user-cont/tool?utm_source=github.com&utm_medium=referral&utm_content=user-cont/tool&utm_campaign=Badge_Grade)

We use this tool to ease our development workflow:

- Fork GitHub repositories
- Create pull requests
- List pull requests
- List local branches and print additional metadata

Configuration is stored in `~/.upsint.json`. Example:

```json
{
  "github": { "token": "abcxyz" },
  "gitlab": { "token": "abcxyz", "ssl_verify": false, "url": "url" }
}
```

## TODO

- List releases
- Check out a PR
- Implement for Gitlab
- Implement for pagure
- Properly implement configuration
- Tests
