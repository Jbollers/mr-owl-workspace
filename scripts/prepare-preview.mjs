// Serve source reports alongside the built UI without duplicating their media.
import { cp, mkdir, symlink, lstat } from 'node:fs/promises';
import { fileURLToPath } from 'node:url';
import path from 'node:path';

const root = fileURLToPath(new URL('..', import.meta.url));
await mkdir(path.join(root, 'dist'), { recursive: true });
await cp(path.join(root, 'public/assets'), path.join(root, 'dist/assets'), { recursive: true });
const link = path.join(root, 'dist/workspace');
if (!await lstat(link).catch(() => null)) await symlink(path.join(root, 'workspace'), link, 'junction');
