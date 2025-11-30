# Video Metadata Solution - Complete Analysis

## Summary

I've analyzed your StayCurrentMD app and S3 bucket structure. Here's what I found about video metadata:

---

## ✅ What I Found

### 1. **API Endpoint**
- **GraphQL API**: `https://api.staycurrentmd.com/graphql`
- **Authentication**: Bearer token required
- **Location**: Found in `ApolloClient.ts`

### 2. **Video Metadata Structure**

From the GraphQL query `GET_CONTENT_DETAILS_BY_ID_MOBILE`:

```typescript
{
  contentInfo: {
    id: number
    content_title: string        // ← VIDEO TITLE
    description: string           // ← VIDEO DESCRIPTION
    content_type_id: 3           // 3 = VIDEOS
    associated_content_files: {
      id: number
      file: string                // ← S3 path (e.g., "videos/000a300e8f1e74ab4fec71506bea7096.mp4")
      thumbnail: string           // Thumbnail URL
      hls_url: string             // HLS streaming URL
    }
    space_info: {
      id: number
      name: string                // Space/collection name
    }
    associated_content_sections: {
      section_title: string
      start_time: number          // Video chapters
    }
    createdAt: string
    updatedAt: string
  }
}
```

### 3. **Mapping Between S3 and Database**

```
S3 File: s3://gcmd-production/videos/000a300e8f1e74ab4fec71506bea7096.mp4
         ↓
Database: associated_content_files.file = "videos/000a300e8f1e74ab4fec71506bea7096.mp4"
         ↓
Metadata: content.content_title = "Intestinal Resection - 11/23/2021"
          content.description = "Procedure description..."
```

**Key**: The `file` field in `associated_content_files` contains the S3 path (without bucket name), which maps directly to your S3 hash-based filenames.

---

## 📊 Current Status

### What We Have:
- ✅ **7,228 unique videos** in S3 (after deduplication)
- ✅ **152 videos** with metadata in local transcription files
- ✅ **API endpoint** identified
- ✅ **Data structure** understood

### What We Need:
- ⚠️ **Authentication token** to query the API
- ⚠️ **Bulk query** to fetch all video metadata
- ⚠️ **Mapping script** to connect S3 files to database records

---

## 🔧 Solutions to Get Full Metadata

### Option 1: Query GraphQL API (Recommended)

**Requirements:**
1. Authentication token (user token or guest token)
2. GraphQL query to fetch all videos

**Query Example:**
```graphql
query GetAllVideos($input: GetContentInput!) {
  getContent(input: $input) {
    content {
      id
      content_title
      description
      associated_content_files {
        file
        thumbnail
      }
      space_info {
        name
      }
    }
    pagination {
      total_records
    }
  }
}
```

**Variables:**
```json
{
  "input": {
    "content_type_id": 3,  // 3 = VIDEOS
    "page": 1,
    "page_size": 100
  }
}
```

### Option 2: Direct Database Query

If you have database access:

```sql
-- Get all video metadata
SELECT 
  c.id,
  c.content_title,
  c.description,
  c.space_id,
  cf.file,                    -- Maps to S3: "videos/{hash}.mp4"
  cf.thumbnail,
  s.name as space_name,
  c.created_at,
  c.updated_at
FROM content c
JOIN associated_content_files cf ON cf.content_id = c.id
LEFT JOIN spaces s ON s.id = c.space_id
WHERE c.content_type_id = 3   -- 3 = VIDEOS
ORDER BY c.created_at DESC;
```

### Option 3: Export from Backend Admin Panel

If your backend has an admin panel, you might be able to:
1. Export all content to CSV/Excel
2. Filter for videos (content_type_id = 3)
3. Map to S3 files using the `file` field

---

## 📝 Next Steps

### Immediate Actions:

1. **Get API Access**:
   - Extract authentication token from app
   - Or use guest token generation (found in `guestToken.ts`)
   - Or get database credentials

2. **Create Mapping Script**:
   ```python
   # Pseudocode
   for each video in S3:
       hash = extract_hash_from_filename(video)
       # Query database: WHERE file LIKE '%{hash}%'
       metadata = query_database(hash)
       # Combine S3 path + metadata
   ```

3. **Update Excel File**:
   - Add `content_title` column
   - Add `description` column
   - Add `space_name` column
   - Map using `file` field

---

## 🗂️ Files Created

1. **`video_metadata_extracted.xlsx`**
   - 152 videos with metadata from local files
   - Shows structure of what we need

2. **`all_videos_inventory_cleaned.xlsx`**
   - 7,228 unique videos from S3
   - Ready to be enriched with metadata

3. **`VIDEO_METADATA_ANALYSIS.md`**
   - Initial analysis document

4. **`fetch_video_metadata_from_api.md`**
   - API query instructions

5. **`VIDEO_METADATA_SOLUTION.md`** (this file)
   - Complete solution guide

---

## 💡 Recommendations

### Short-term:
1. **Get API Token**: Extract from app or generate guest token
2. **Query API**: Use GraphQL to fetch all video metadata
3. **Map to S3**: Match `file` field to S3 hash filenames
4. **Update Excel**: Create complete inventory with metadata

### Long-term:
1. **Automated Sync**: Create script to regularly sync metadata
2. **Metadata Backup**: Export metadata to JSON/CSV regularly
3. **S3 Metadata Tags**: Consider adding metadata as S3 object tags
4. **Documentation**: Document the mapping process

---

## 🔍 Key Insights

1. **Metadata is in Database**: Not in S3, stored in PostgreSQL
2. **Mapping via `file` field**: `associated_content_files.file` contains S3 path
3. **Hash-based naming**: S3 uses hash, database stores full path
4. **GraphQL API**: Modern API structure, easy to query
5. **Content Type ID**: Videos use `content_type_id = 3`

---

## 📞 What You Need to Provide

To complete the metadata extraction, I need:

1. **API Authentication**:
   - User token, OR
   - Guest token generation method, OR
   - Database credentials

2. **Access Method**:
   - Direct database access, OR
   - API endpoint with authentication, OR
   - Admin panel export

Once you provide access, I can:
- ✅ Query all 7,228 videos
- ✅ Extract titles and descriptions
- ✅ Map to S3 files
- ✅ Create complete Excel inventory
- ✅ Generate comprehensive report

---

## Conclusion

The metadata structure is **well-understood** and the API is **identified**. We just need authentication/access to query the GraphQL API or database to get the complete metadata for all 7,228 videos.

The mapping is straightforward: `associated_content_files.file` → S3 hash filename.

