# هذا الملف يحتوي على قوالب GitHub Actions لمختلف أنواع المشاريع

WORKFLOW_FLUTTER = """
name: Flutter Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '17'
      - uses: subosito/flutter-action@v2
        with:
          flutter-version: '3.10.0'
          channel: 'stable'
      - run: flutter pub get
      - run: flutter build apk --release
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: build/app/outputs/flutter-apk/app-release.apk
"""

WORKFLOW_REACT_NATIVE = """
name: React Native Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-node@v3
        with:
          node-version: '18'
      - uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '17'
      - run: npm install
      - run: cd android && ./gradlew assembleRelease
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: android/app/build/outputs/apk/release/app-release.apk
"""

WORKFLOW_ANDROID_NATIVE = """
name: Android Native Build APK
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '17'
      - run: chmod +x gradlew
      - run: ./gradlew assembleRelease
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: app/build/outputs/apk/release/app-release.apk
"""

WORKFLOW_WEB_TO_APK = """
name: Web to APK (WebView)
on: [push]
jobs:
  build:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v3
      - name: Setup Java
        uses: actions/setup-java@v3
        with:
          distribution: 'zulu'
          java-version: '17'
      - name: Clone WebView Template
        run: |
          git clone https://github.com/fazle-rabbi-dev/Html-Css-Js-Web-View-Apk-Template template
          cp -r . template/app/src/main/assets/ || true
          cd template
          chmod +x gradlew
          ./gradlew assembleRelease
      - name: Upload APK
        uses: actions/upload-artifact@v3
        with:
          name: app-release
          path: template/app/build/outputs/apk/release/app-release-unsigned.apk
"""

def get_workflow(project_type):
    if project_type == "Flutter":
        return WORKFLOW_FLUTTER
    elif project_type == "React Native":
        return WORKFLOW_REACT_NATIVE
    elif project_type == "Android Native":
        return WORKFLOW_ANDROID_NATIVE
    elif project_type == "Web (HTML)":
        return WORKFLOW_WEB_TO_APK
    else:
        return WORKFLOW_ANDROID_NATIVE # الافتراضي
