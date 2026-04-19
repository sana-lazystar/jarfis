# AWS Cognito Expertise

> 사용자 인증 — User Pool vs Identity Pool, JWT 검증, MFA, custom attributes

## Common Pitfalls
- **User Pool vs Identity Pool 혼동**: User Pool = 인증(sign-up/in), Identity Pool = AWS 리소스 접근용 IAM credentials. 둘 다 쓰면 User Pool 토큰 → Identity Pool 교환.
- **JWT `alg: none` 또는 `HS256` 허용**: Cognito는 `RS256` 사용. 검증 라이브러리가 `algorithms: ['RS256']` 명시 안 하면 토큰 위조 가능.
- **`aud` claim 미검증**: ID token `aud` = App Client ID, Access token은 `client_id`. 둘 다 체크.
- **Token revocation 지연**: JWT expiry까지 서버는 유효 간주. **강제 로그아웃**은 Cognito `AdminUserGlobalSignOut` + 서버측 blacklist(Redis).
- **Custom attribute 수정 불가**: `Mutable: true`로 만들지 않으면 이후 변경 불가. User Pool 재생성 아니면 수정 불가.

## Decision Heuristics
- MFA: SMS < TOTP (Authenticator app) < WebAuthn/Passkeys (2024+). 금융/민감 → TOTP 필수.
- Custom attributes: 15개 하드캡. 프로필 확장은 DynamoDB에 userSub 매핑 권장.
- Lambda triggers: `PreSignUp`, `PreTokenGeneration`, `PostConfirmation` 등 — 비동기 side effect는 triggers가 아닌 별도 Lambda + SNS.
- Federation: Google/Apple/SAML → Hosted UI 가장 빠름. Custom UI는 SDK + OAuth 수동 구현.

## Anti-patterns
- **User Pool password에 추가 hash 저장**: Cognito가 이미 해시. 중복 저장 금지.
- **Refresh token 클라이언트 localStorage 저장**: XSS 노출. HttpOnly cookie + CSRF 방어.
- **Access token을 API Gateway `Authorizer`에 넣지 않고 자체 Lambda 검증**: JWT verification 누락 많음. `COGNITO_USER_POOLS` authorizer 사용.

## Version & Environment Notes
- Advanced Security: adaptive auth, compromised credentials 감지. User Pool tier "Plus" (2024+) 필요.
- Cognito Sync (legacy, deprecated) → AppSync 이동.
- Hosted UI 커스터마이징: CSS만 가능. JS/HTML 삽입 불가 → 완전 커스텀은 직접 OIDC 구현.

## Related Skills
- `aws-lambda` (triggers + JWT 검증), `dynamodb` (사용자 확장 프로필), `s3` (Identity Pool로 사용자별 접근)
