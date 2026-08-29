# Third-party material

The files under `patches/` are research evidence. They contain small source excerpts from the upstream projects below at the revisions recorded in `data/subjects.csv` and the patch manifests. The excerpts remain governed by the corresponding upstream terms.

| Project | License/notice retained here |
|---|---|
| [Accenture/mercury](https://github.com/Accenture/mercury) | `third_party/licenses/Accenture__mercury/LICENSE` |
| [Alluxio/alluxio](https://github.com/Alluxio/alluxio) | `third_party/licenses/Alluxio__alluxio/LICENSE` |
| [TooTallNate/Java-WebSocket](https://github.com/TooTallNate/Java-WebSocket) | `third_party/licenses/TooTallNate__Java-WebSocket/LICENSE` |
| [alibaba/wasp](https://github.com/alibaba/wasp) | `third_party/licenses/alibaba__wasp/` |
| [apache/dubbo](https://github.com/apache/dubbo) | `third_party/licenses/apache__dubbo/` |
| [apache/httpcore](https://github.com/apache/httpcore) | `third_party/licenses/apache__httpcore/` |
| [apache/incubator-uniffle](https://github.com/apache/incubator-uniffle) | `third_party/licenses/apache__incubator-uniffle/` |
| [elasticjob/elastic-job-lite](https://github.com/elasticjob/elastic-job-lite) | `third_party/licenses/elasticjob__elastic-job-lite/` |
| [flaxsearch/luwak](https://github.com/flaxsearch/luwak) | `third_party/licenses/flaxsearch__luwak/LICENSE` |
| [fluent/fluent-logger-java](https://github.com/fluent/fluent-logger-java) | `third_party/licenses/fluent__fluent-logger-java/LICENSE.txt` |
| [kagkarlsson/db-scheduler](https://github.com/kagkarlsson/db-scheduler) | `third_party/licenses/kagkarlsson__db-scheduler/` |
| [nlighten/tomcat_exporter](https://github.com/nlighten/tomcat_exporter) | `third_party/licenses/nlighten__tomcat_exporter/LICENSE` |
| [qos-ch/logback](https://github.com/qos-ch/logback) | `third_party/licenses/qos-ch__logback/LICENSE.txt` |

At the pinned db-scheduler revision, the project declares Apache License 2.0 in `pom.xml` and retains a `NOTICE` file but no top-level license text. Its directory here therefore includes that upstream notice plus the canonical Apache License 2.0 text.

Developer-comparator provenance is more specific: `patches/comparator_manifest.csv` records the source commit URL, commit hash, relationship to the study case, and content hashes. Repeated Alluxio case instances intentionally point to the same independent repair design.
