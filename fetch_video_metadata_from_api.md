# How to Fetch Video Metadata from StayCurrentMD API

## Data Structure Discovered

From analyzing the StayCurrentMD Mobile app codebase, I found the GraphQL API structure:

### GraphQL Query Structure

```graphql
query GetContentInfoById($input: GetContentInfoByIdInput!) {
  getContentInfoById(input: $input) {
    contentInfo {
      id
      content_title          # ← Video Title
      description            # ← Video Description
      content_type_id
      associated_content_files {
        id
        file                 # ← S3 file path (hash-based filename)
        thumbnail            # ← Thumbnail URL
        hls_url              # ← HLS streaming URL
      }
      associated_content_sections {
        id
        section_title
        start_time
      }
      space_info {
        id
        name
      }
      createdAt
      updatedAt
    }
  }
}
```

### Key Fields for Video Metadata

1. **`content_title`** - The video title
2. **`description`** - Video description
3. **`associated_content_files.file`** - S3 file path (maps to hash-based filename)
4. **`associated_content_files.thumbnail`** - Thumbnail image URL
5. **`space_info.name`** - Space/collection name
6. **`associated_content_sections`** - Video chapters/sections

---

## How to Get All Video Metadata

### Option 1: Query GraphQL API Directly

You'll need:
1. **API Endpoint**: Found in `ApolloClient.ts` or `config.ts`
2. **Authentication Token**: User token or guest token
3. **GraphQL Query**: Use `GET_CONTENT_DETAILS_BY_ID_MOBILE` or create a bulk query

### Option 2: Query Database Directly

If you have database access, the schema likely looks like:

```sql
-- Content table (videos are content with content_type_id = 3)
SELECT 
  c.id,
  c.content_title,
  c.description,
  c.content_type_id,
  c.space_id,
  c.created_at,
  c.updated_at
FROM content c
WHERE c.content_type_id = 3  -- 3 = VIDEOS (from contentTypeIds.ts)
ORDER BY c.created_at DESC;

-- Content files table (maps to S3)
SELECT 
  cf.id,
  cf.content_id,
  cf.file,              -- Hash-based filename (e.g., "000a300e8f1e74ab4fec71506bea7096.mp4")
  cf.thumbnail,
  cf.hls_url
FROM associated_content_files cf
JOIN content c ON cf.content_id = c.id
WHERE c.content_type_id = 3;
```

### Option 3: Use the App's API

The app uses Apollo Client with GraphQL. You can:

1. **Find API URL**: Check `ApolloClient.ts` for the GraphQL endpoint
2. **Get Auth Token**: Extract from app storage or use guest token
3. **Query All Videos**: Create a query to fetch all video content

---

## Mapping S3 Files to Metadata

The mapping works like this:

```
S3 File: s3://gcmd-production/videos/000a300e8f1e74ab4fec71506bea7096.mp4
         ↓
Database: associated_content_files.file = "videos/000a300e8f1e74ab4fec71506bea7096.mp4"
         ↓
Metadata: content.content_title = "Intestinal Resection - 11/23/2021"
          content.description = "..."
```

---

## Next Steps

1. **Find API Endpoint**: Check `ApolloClient.ts` for the GraphQL URL
2. **Get Authentication**: Determine how to authenticate (token, guest token, etc.)
3. **Create Bulk Query**: Query all videos at once or in batches
4. **Map to S3**: Match `associated_content_files.file` to S3 hash filenames
5. **Update Excel**: Add metadata to `all_videos_inventory_cleaned.xlsx`

---

## Files to Check

1. `/StayCurrentMD Mobile/staycurrent-mobile/src/services/ApolloClient.ts` - API endpoint
2. `/StayCurrentMD Mobile/staycurrent-mobile/src/utils/config.ts` - Configuration
3. `/StayCurrentMD Mobile/staycurrent-mobile/src/services/QueryMethod.ts` - GraphQL queries
4. Backend database schema (if accessible)

