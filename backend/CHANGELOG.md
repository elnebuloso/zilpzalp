# Changelog

## [0.2.2](https://github.com/elnebuloso/zilpzalp/compare/v0.2.1...v0.2.2) (2026-06-14)


### Bug Fixes

* add package docstring and cut 0.2.2 to validate CI pipeline ([1aef065](https://github.com/elnebuloso/zilpzalp/commit/1aef06593bd2b268519525f070abee27bbbfb617))

## [0.2.1](https://github.com/elnebuloso/zilpzalp/compare/v0.2.0...v0.2.1) (2026-06-14)


### Bug Fixes

* **tests:** assert __version__ matches package metadata, not a pinned literal ([0f44e01](https://github.com/elnebuloso/zilpzalp/commit/0f44e014ffc7bf9b91d6d3a580fc209d916cfd15))

## [0.2.0](https://github.com/elnebuloso/zilpzalp/compare/v0.1.0...v0.2.0) (2026-06-14)


### Features

* **analyzer:** apply optional config date_patterns additively ([8285153](https://github.com/elnebuloso/zilpzalp/commit/8285153e8b58619776ffb125fab667ac270f32f6))
* **analyzer:** capture context snippet per date candidate ([fa2a583](https://github.com/elnebuloso/zilpzalp/commit/fa2a5833b903c17a138b3ba131f6b60a99f78d86))
* **analyzer:** collect & normalize numeric/ISO date candidates ([d49935a](https://github.com/elnebuloso/zilpzalp/commit/d49935a48d95d8316cb0e468e56d3d33987b5ec0))
* **analyzer:** derive structural labels for date candidates ([821b400](https://github.com/elnebuloso/zilpzalp/commit/821b400141d7f02694405eb00967952f36407340))
* **analyzer:** heuristics for sender and doctype ([5c32939](https://github.com/elnebuloso/zilpzalp/commit/5c32939d94a9b00a15b65f0897b700500186c74f))
* **analyzer:** recognize German long-form dates and 2-digit years ([f709fa8](https://github.com/elnebuloso/zilpzalp/commit/f709fa83ae05f05bbe5098ad27fedddc8000aa19))
* **backend:** load config at FastAPI startup with /health route ([62a72d4](https://github.com/elnebuloso/zilpzalp/commit/62a72d4ca06320ecb9b3c423dbc09be7999db6e0))
* **config:** add atomic save_config with load-equivalent validation ([4251c37](https://github.com/elnebuloso/zilpzalp/commit/4251c379ea91ce39a5fe00095c4f03e60cc1ac58))
* **config:** load and parse config.yaml into a typed model ([0a53470](https://github.com/elnebuloso/zilpzalp/commit/0a53470dcfab8b0ff58e6e176bbd8f67d8e6d0da))
* **config:** validate date_format directive ([a57e099](https://github.com/elnebuloso/zilpzalp/commit/a57e099d93a540cf41fcbd08b1874e04ece9a4e0))
* **config:** validate optional date_patterns regex ([d9d74cc](https://github.com/elnebuloso/zilpzalp/commit/d9d74ccde7a2c1a77d137b9e6795f75e5e179c19))
* **config:** validate pattern placeholders ([7745745](https://github.com/elnebuloso/zilpzalp/commit/77457456d9ac533d347de22338a02a899716d48c))
* **config:** validate required paths exist ([f632042](https://github.com/elnebuloso/zilpzalp/commit/f632042471f8a111add041a61495f76f7a40fbcd))
* **config:** wrap load and parse failures in a clear ConfigError ([75c8633](https://github.com/elnebuloso/zilpzalp/commit/75c86333f4d5a8b7b9d4a1ebd806198be06d4109))
* **document:** add Block/Document model ([02a1f60](https://github.com/elnebuloso/zilpzalp/commit/02a1f60f76965993bc141e3a3c2a673a7adac32a))
* **extractor:** extract() with JVM call, temp cleanup, no-text error ([da8d37e](https://github.com/elnebuloso/zilpzalp/commit/da8d37eeb62cadb9f1604bd49f54a9c15c094361))
* **extractor:** map ODL JSON to Document (simple elements) ([e8581fa](https://github.com/elnebuloso/zilpzalp/commit/e8581fae424dfc18aaaec471c9fed2a7b52b3ccf))
* **extractor:** map ODL tables to Block.cells ([f85b6c1](https://github.com/elnebuloso/zilpzalp/commit/f85b6c10af7d60768a1699577101e26d5a39f3a1))
* **main:** start watcher and expose queue on app startup ([cbdc3d3](https://github.com/elnebuloso/zilpzalp/commit/cbdc3d31b0f03b2294dd37939f3b4a87ae96316d))
* **main:** track startup completion via app.state.started ([2429cdb](https://github.com/elnebuloso/zilpzalp/commit/2429cdb42712b65370ae104f372d2f7383f9d566))
* **processor:** copy PDF to target folders, keep original ([82bfbd8](https://github.com/elnebuloso/zilpzalp/commit/82bfbd84a5c3d23294ea8de26996112320f3c83e))
* **processor:** copy PDF to target folders, keep original ([ed24ecc](https://github.com/elnebuloso/zilpzalp/commit/ed24eccd93bdb96ee3847d237d549d7dc1f2e279))
* **processor:** guard against empty/missing targets and processed overwrite ([3c6651e](https://github.com/elnebuloso/zilpzalp/commit/3c6651ec69dfd16f9f1f896e93383ee76c208ae4))
* **processor:** handle original via move and delete ([7d290d8](https://github.com/elnebuloso/zilpzalp/commit/7d290d801449b51d54639cf2fb9e9af3dd6d4e91))
* **processor:** reject name conflicts without auto-suffix ([be2ebe0](https://github.com/elnebuloso/zilpzalp/commit/be2ebe06b5eb0de33889de4d1b341561099a3671))
* **queue:** add stable id, ready/analyzing status and cached suggestion ([f6e5a68](https://github.com/elnebuloso/zilpzalp/commit/f6e5a68c7f5e73483d81ea58a9461a671da4e528))
* **queue:** in-memory pending register with path dedup ([ebd48fe](https://github.com/elnebuloso/zilpzalp/commit/ebd48fecd252f1d49f66a6711aacc2388df9a2d1))
* **suggestion:** resolve rule and default target folders ([e9672ea](https://github.com/elnebuloso/zilpzalp/commit/e9672ea92c7548b6e3857a77ef6a5c46994546d8))
* **suggestion:** rule matching, apply overrides, preferred_date ([c34d2c7](https://github.com/elnebuloso/zilpzalp/commit/c34d2c7acbebe4e0f2f2361e5e125c8e7d802948))
* **suggestion:** Suggestion type with default pattern rendering ([9c5a367](https://github.com/elnebuloso/zilpzalp/commit/9c5a3670839716156c914b7c5582b66fa98a0074))
* **watcher:** expose is_alive() for health probes ([8c02423](https://github.com/elnebuloso/zilpzalp/commit/8c02423177ee45e191bfa32552ad4624771015fa))
* **watcher:** watchdog observer plus initial folder scan ([5194ed8](https://github.com/elnebuloso/zilpzalp/commit/5194ed8af641affd7c1ce438605797a895fe624e))
* **web:** add /healthz startup, ready, live probes ([c2c606c](https://github.com/elnebuloso/zilpzalp/commit/c2c606c8869bc12ffeb4648ee5c93db091c2fb19))
* **web:** add i18n catalogs and translate/resolve_language helpers ([60ba956](https://github.com/elnebuloso/zilpzalp/commit/60ba956432c0c467791d94c177500969ae673512))
* **web:** add language switcher, /lang route and per-request language ([230fb2a](https://github.com/elnebuloso/zilpzalp/commit/230fb2ad67b8b059f2875623c146913d3cd18a4f))
* **web:** add shared filename builder and web dependencies ([d6f38f7](https://github.com/elnebuloso/zilpzalp/commit/d6f38f7c7b0f7ffd5be5ce7bf2ee0c22af51bd1a))
* **web:** configuration editor with save + validation feedback ([46935ae](https://github.com/elnebuloso/zilpzalp/commit/46935ae8c8ce34602892afb17963239ed4ba29f2))
* **web:** confirm/summary/conflict flow with server-side execution ([34383f1](https://github.com/elnebuloso/zilpzalp/commit/34383f1aec436dad93d4d32292dbd18233f1fb2e))
* **web:** default to dark theme on first visit ([5440d1f](https://github.com/elnebuloso/zilpzalp/commit/5440d1fea26e77b45a9c4babbc886405f4b12aa6))
* **web:** localize flash messages and summary modal ([57f1929](https://github.com/elnebuloso/zilpzalp/commit/57f19292840161cf2ba8f56187b28df3f0b500ca))
* **web:** localize review hint messages in app.js ([269817b](https://github.com/elnebuloso/zilpzalp/commit/269817bac03bb7aa483313153d23141ee72aa1f7))
* **web:** overview page with counters, betriebsangaben and polling ([23ffb57](https://github.com/elnebuloso/zilpzalp/commit/23ffb57bd785a44edb0274b0fb1f0c338dc2d4d8))
* **web:** queue page with self-refreshing list ([a9fe72c](https://github.com/elnebuloso/zilpzalp/commit/a9fe72c6b796fae0905ee4b281d04fd8c7f7edd3))
* **web:** review page with all date candidates and live-preview form ([6035202](https://github.com/elnebuloso/zilpzalp/commit/60352025e8e98dde66d53238a3ffd674766ed89a))
* **web:** serve static assets + base shell, wire worker into app ([eaa1a80](https://github.com/elnebuloso/zilpzalp/commit/eaa1a80eb870ecebe02e51bf5836397e131840d9))
* **worker:** add single-thread extract→analyze→suggest worker ([32b36f4](https://github.com/elnebuloso/zilpzalp/commit/32b36f426ef093ebc7d94c3245514ebba812d7c1))
* **worker:** expose is_alive() for health probes ([f84a00c](https://github.com/elnebuloso/zilpzalp/commit/f84a00c289a0aad5565373a24fa3c8c58e5f61f7))


### Bug Fixes

* **config:** chain exceptions and catch UnicodeDecodeError in load_config ([da2a440](https://github.com/elnebuloso/zilpzalp/commit/da2a440652e62bd1e3a5dbec5fa6d524211e88a5))
* **queue:** make mark_error symmetric — no-op when unknown, clear suggestion ([f39ce10](https://github.com/elnebuloso/zilpzalp/commit/f39ce1043c3f7ced17dfbafcd7d7461f2c03a1f8))
* **watcher:** stop observer if initial scan fails ([400e9bc](https://github.com/elnebuloso/zilpzalp/commit/400e9bcfe0a8e184a7ad1bbccd9c271c9a1165c0))
* **web:** format rename date via config.date_format for candidates; drop german_date display filter ([9a86d72](https://github.com/elnebuloso/zilpzalp/commit/9a86d728214c1653cc70d633dfce01d508b31b22))
* **web:** mark conflicting target on execute-race; keep full snippet tail ([5fd7266](https://github.com/elnebuloso/zilpzalp/commit/5fd726621328877292f720f8570ab0a7733cf6bd))
* **web:** reject protocol-relative next in /lang to prevent open redirect ([8d6417f](https://github.com/elnebuloso/zilpzalp/commit/8d6417ffa13a19fc1f9f7d053c5a0e2567aa55f8))
