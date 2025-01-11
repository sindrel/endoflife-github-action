<p align="center">
  <img src="assets/eol-action-logo.png" width="140px" height="140px" />
  <h2 align="center">End-of-Life GitHub Action</h2>
  <p align="center">Source running versions of components from files in your repository. Get notified when they're no longer being maintained.</p>
</p>

## Features

- Fetches product cycle information from the [endoflife.date API](https://endoflife.date).
- Supports version extraction from YAML, JSON, or plain text files.
- Allows for failure conditions based on end-of-life status and days until end-of-life.
- Outputs can be used in subsequent steps, e.g. for pushing notifications or raising alerts.

## Inputs

| Input          | Required | Description                                                                 |
|----------------|----------|-----------------------------------------------------------------------------|
| `product`      | Yes      | The product ID (see the URL on https://endoflife.date).                   |
| `file_path`    | No       | Path to the file containing the version information.                        |
| `file_key`     | No       | Key used to extract the version from a file if YAML or JSON (e.g. `image.tag`). |
| `file_format`  | No       | Format of the file containing the version information. Default is `yaml`.  |
| `version`      | No       | If not extracting from a file, the version can be provided directly.                 |
| `regex`        | No       | Regular expression to capture a group in any file.                         |
| `fail_on_eol`  | No       | Whether to fail if the end-of-life date has passed. Default is `false`.   |
| `fail_days_left` | No     | Fail the action if the end-of-life date is less than this number of days away. |

## Outputs

| Output           | Description                                                                |
|------------------|----------------------------------------------------------------------------|
| `end_of_life`    | Whether the end-of-life date has passed or not ('true', 'false').                            |
| `version`        | The version extracted from file (if not provided).                         |
| `days_until_eol` | The number of days until the end-of-life date (negative if passed).        |
| `text_summary`   | A brief summary of the end-of-life status.                                 |

## Usage examples

### Example A: Notify on Slack if there's 30 days left until end-of-life

```yaml
# .github/workflows/myworkflow.yml
name: Notify on Slack
on:
  schedule:
   - cron: '0 10 * * *'
  
jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout
        uses: actions/checkout@v3

      - uses: sindrel/endoflife-github-action@latest
        name: Check when Prometheus is end-of-life
        id: endoflife
        with:
          product: 'prometheus'
          file_path: 'helm/values.yaml'
          file_key: 'image.tag'

      - name: Notify when 30 days until end-of-life
        if: steps.endoflife.outputs.days_until_eol == 30
        uses: slackapi/slack-github-action@v2.0.0
        with:
          method: chat.postMessage
          token: ${{ secrets.SLACK_BOT_TOKEN }}
          payload: |
            channel: ${{ secrets.SLACK_CHANNEL_ID }}
            text: ":warning: ${{ steps.endoflife.outputs.text_summary }}"
```

##### This would produce a Slack notification:  
<img src="assets/slack-notification.png" alt="Slack Notification" width="400"/>

#### You can use the same pattern for similar use-cases, like:
* Raising an incident in PagerDuty, or
* Creating an issue for follow-up in GitHub or Jira

### Example B: Fail the workflow if the end-of-life date has passed

```yaml
# .github/workflows/myworkflow.yml
name: Fail if end-of-life

on:
  push:
    branches:
      - main

jobs:
  check-eol:
    runs-on: ubuntu-latest
    steps:
      - name: Checkout code
        uses: actions/checkout@v2

      - name: Fail if end-of-Life
        uses: sindrel/endoflife-github-action@latest
        with:
          product: 'your-product-id'
          file_path: 'path/to/your/version/file.yaml'
          file_key: 'image.tag'
          fail_on_eol: 'true'
```
This could be run on a schedule, or as part of a CI pipeline.


## Extracting version from a YAML or JSON file

The action supports simple extraction of versions from YAML or JSON formatted files.

#### Key pattern

The `file_key` input takes in the path to a value you wish to extract. For instance, if you have a Helm values file like this:

```yaml
# helm/values.yaml
image:
  repository: prom/prometheus
  tag: v2.55.1
```

To extract the value that contains the version, specify the key as `image.tag`, meaning it's the `tag` value in the `image` stanza.

Here’s an example of how to use it in a workflow (for JSON, set `file_format` to `json`):

```yaml
# .github/workflows/myworkflow.yml
# ...
      - name: Check end-of-Life for Prometheus
        uses: sindrel/endoflife-github-action@latest
        with:
          product: 'prometheus'
          file_path: 'helm/values.yaml'
          file_key: 'image.tag'
          file_format: 'yaml'
```

## Extracting the version from any file using a regular expression

It's possible to extract a version from any plaintext file using the `regex` input.

Let's say you have a XML document that contains a version you wish to extract:

```xml
<!-- path/to/your/file.xml -->
<software>
  <repository>graylog</repository>
  <version>v5.2.12</version>
</software>
```

To extract the version value, you can provide a regular expression. In this example any first match on a string that seems to be a semantic version prefixed with `v` is used: in this case `v5.2.12`. (Note that your use case might require something a bit more complex):

```yaml
# .github/workflows/myworkflow.yml
# ...
      - name: Check end-of-life for Graylog
        uses: sindrel/endoflife-github-action@latest
        with:
          product: 'graylog'
          file_path: 'path/to/your/file.xml'
          regex: 'v([0-9]+\.[0-9]+\.[0-9]+)'
```

## Provide the version manually

If you are using other methods to extract the version, or wish to hardcode it into your workflow, you can use the `version` input to provide the version manually.

```yaml
# .github/workflows/myworkflow.yml
# ...
      - name: Check end-of-life for a product
        uses: sindrel/endoflife-github-action@latest
        with:
          product: 'the-product'
          version: 'v1.2.3'
```

## Matching semantic versions

If the version used is semantic (e.g. `v1.2.3`), the action will attempt to match cycles from patch to major. This means that you don't have to strip the patch version where the product's release cycles apply to major or minor versions.

* If no direct match on `1.2.3`, it will attempt to match `1.2`
* If no direct match on `1.2`, it will attempt to match `1`

## Failure conditions

The default behavior of the action is to **not fail** if a product cycle is end-of-life.

* Set the `fail_on_eol` input to `true` to have the workflow fail if a product has passed it's end-of-life date.
* To have the workflow fail as an early warning, use the `fail_days_left` input to specify how many days in advance you wish the workflow to fail.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE.md) file for details.

## Contributing

Contributions are welcome! Please open an issue or submit a pull request for any enhancements or bug fixes.