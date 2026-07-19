#!/bin/sh
# Podcast Clips Gradle wrapper launcher. The JAR is materialized only by the reviewed remote workflow.
APP_HOME=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd -P) || exit 1
JAVA_CMD=${JAVA_HOME:+$JAVA_HOME/bin/}java
if ! command -v "$JAVA_CMD" >/dev/null 2>&1; then
  printf '%s
' "Java 17 is required." >&2
  exit 1
fi
exec "$JAVA_CMD" -Xmx64m -Xms64m -Dorg.gradle.appname=gradlew -classpath "$APP_HOME/gradle/wrapper/gradle-wrapper.jar" org.gradle.wrapper.GradleWrapperMain "$@"
