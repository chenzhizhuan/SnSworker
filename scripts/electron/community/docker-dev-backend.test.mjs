import assert from 'node:assert/strict';
import path from 'node:path';
import { test } from 'node:test';

import {
  createDockerDevEnvironment,
  resolveDockerDevComposeArgs,
} from './docker-dev-backend.mjs';

test('Docker dev Compose uses the root env file and ignores shell edition overrides', () => {
  const args = resolveDockerDevComposeArgs('/repo');
  const env = createDockerDevEnvironment({
    baseEnv: {
      TABTIN_EDITION: 'saas',
      AUTH_FIXED_VERIFICATION_CODE: '123456',
      PATH: '/usr/bin',
    },
    fingerprint: 'fixture',
  });

  assert.deepEqual(args.slice(0, 5), [
    'compose',
    '--project-directory',
    '/repo',
    '--env-file',
    // 期望值用 path.join 动态计算：win32 语义下 join('/repo','.env') 为 '\repo\.env'，
    // 与实现一致；POSIX 下为 '/repo/.env'。断言意图是 env-file 指向 root 下的 .env。
    path.join('/repo', '.env'),
  ]);
  assert.equal(Object.hasOwn(env, 'TABTIN_EDITION'), false);
  assert.equal(Object.hasOwn(env, 'AUTH_FIXED_VERIFICATION_CODE'), false);
  assert.equal(env.PATH, '/usr/bin');
  assert.equal(env.TABTIN_DEV_DEPENDENCY_FINGERPRINT, 'fixture');
});
