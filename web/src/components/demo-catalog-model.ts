// web/src/components/demo-catalog-model.ts
// Shapes of a demo bundle and of an instance as the catalog and its dialogs use them.
// Author: Pierre Grothe
// Date: 2026-11-07

export interface DemoBundle {
  manifest: {
    id: string
    name: string
    version: string
    description: string
    sn_release: string
    min_release?: string
    required_plugins: string[]
    tags: string[]
    author?: string
    created_at?: string
    personas?: Array<{ name: string; role: string; email: string }>
  }
  bundle_path: string
  owner_email?: string
  access?: 'owner' | 'shared'
  version?: number
  fluent_files: string[]
  seed_files: string[]
  has_walkthrough: boolean
  media_captures?: Array<{
    id: string
    bundle_id: string
    instance_url: string
    target_path: string
    media_type: 'screenshot' | 'video'
    label: string
    filename: string
    url: string
    engine: string
    created_at?: string
  }>
}

export interface CatalogInstance {
  id: string
  name: string
  release: string
  is_default: boolean
}
