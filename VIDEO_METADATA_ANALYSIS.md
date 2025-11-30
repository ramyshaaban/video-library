# Video Metadata Analysis - StayCurrentMD

## Executive Summary

I've analyzed the video metadata situation for your StayCurrentMD app. Here's what I found:

### Current State
- ✅ **152 videos** have metadata in local transcription files
- ❌ **7,228 videos** exist in S3 (only 2% have metadata locally)
- ⚠️ **Metadata gap**: Most video metadata is stored in the database, not in S3 or local files

---

## Metadata Sources

### 1. Local Transcription Files (152 videos)
**Location**: `videos/*.json` files

**Contains**:
- ✅ Titles (e.g., "Intestinal Resection - 11/23/2021")
- ✅ File URLs (e.g., "spaces/4/content/4671/file_5908_2021-11-23_16-00-13.mp4")
- ✅ Specialties (surgery, neonatal, pediatric, etc.)
- ✅ Procedure types (Appendectomy, Gastrostomy, etc.)
- ✅ Complexity levels
- ✅ Keywords

**Limitation**: These reference a different file naming pattern than S3 hash-based names.

### 2. S3 Bucket (7,228 videos)
**Location**: `gcmd-production/videos/` and `gcmd-production/vimeo_videos/`

**Contains**:
- ✅ Video files (hash-based filenames)
- ✅ Thumbnails
- ❌ **No metadata files** (metadata stored in database)

### 3. Database (Primary Source)
**Location**: PostgreSQL database (referenced in `.env` files)

**Likely Contains**:
- Video metadata (title, description, specialty, etc.)
- Hash-to-metadata mapping
- Content IDs
- User associations
- View statistics

---

## The Mapping Challenge

### Problem
The S3 videos use **hash-based filenames**:
```
000a300e8f1e74ab4fec71506bea7096.mp4
```

But the local metadata references **original filenames**:
```
file_5908_2021-11-23_16-00-13.mp4
```

### Solution
The database likely contains the mapping:
```sql
videos table:
  - id
  - hash (maps to S3 filename)
  - original_filename (maps to metadata)
  - title
  - description
  - specialty
  - ...
```

---

## Metadata Statistics (From Local Files)

### By Specialty
- **Surgery**: ~80 videos
- **Neonatal**: ~8 videos
- **Pediatric**: ~10 videos
- **ECMO**: ~12 videos
- **Unknown**: ~42 videos

### By Procedure Type
1. Appendectomy Procedure
2. Gastrostomy Tube Placement
3. Central Line Placement
4. Vascular Access Surgery
5. Cardiac Surgery
6. And more...

### Sample Titles
- "Intestinal Resection - 11/23/2021"
- "Emergency Trauma Surgery - 8/23/2022"
- "Gastrostomy Tube Placement - 10/20/2022"
- "Cardiac Surgery - 10/20/2022"
- "Appendectomy Procedure - 8/23/2022"

---

## How to Get Full Metadata

### Option 1: Database Query (Recommended)
Query your PostgreSQL database directly:

```sql
SELECT 
  v.id,
  v.hash,
  v.title,
  v.description,
  v.specialty,
  v.procedure_type,
  v.complexity,
  v.created_at,
  v.s3_path
FROM videos v
ORDER BY v.created_at DESC;
```

### Option 2: API Endpoint
If your app has a REST API, query it:

```bash
# Example API call
curl https://your-api.com/api/videos \
  -H "Authorization: Bearer YOUR_TOKEN"
```

### Option 3: Database Export
Export the videos table to CSV/Excel:

```sql
COPY (
  SELECT * FROM videos
) TO '/tmp/videos_export.csv' WITH CSV HEADER;
```

### Option 4: App Code Analysis
Check the StayCurrentMD mobile app codebase for:
- API endpoints that fetch video metadata
- Database models/schemas
- Data fetching functions

---

## Files Created

1. **`video_metadata_extracted.xlsx`**
   - All 152 videos with metadata from local files
   - Summary statistics
   - Grouped by specialty and procedure type

2. **`VIDEO_METADATA_ANALYSIS.md`** (this file)
   - Complete analysis and recommendations

---

## Recommendations

### Immediate Actions
1. ✅ **Query Database**: Export all video metadata from PostgreSQL
2. ✅ **Create Mapping**: Map database records to S3 hash filenames
3. ✅ **Update Excel**: Add metadata to `all_videos_inventory_cleaned.xlsx`

### Long-term Solutions
1. **API Endpoint**: Create an API endpoint to fetch video metadata
2. **Metadata Sync**: Regularly sync database metadata to a local file
3. **S3 Metadata**: Consider storing minimal metadata as S3 object metadata
4. **Documentation**: Document the hash-to-metadata mapping process

---

## Next Steps

To get the full metadata for all 7,228 videos:

1. **Access Database**:
   ```bash
   # Connect to your PostgreSQL database
   psql $DATABASE_URL
   ```

2. **Export Video Metadata**:
   ```sql
   SELECT * FROM videos;
   ```

3. **Map to S3 Files**:
   - Use the `hash` field to match S3 filenames
   - Combine with S3 inventory Excel file

4. **Create Complete Inventory**:
   - Merge database metadata with S3 file list
   - Create comprehensive Excel file with all metadata

---

## Database Schema (Inferred)

Based on the app structure and local metadata, the database likely has:

```sql
CREATE TABLE videos (
  id SERIAL PRIMARY KEY,
  hash VARCHAR(32) UNIQUE,  -- Maps to S3 filename
  title VARCHAR(255),
  description TEXT,
  specialty VARCHAR(100),
  procedure_type VARCHAR(100),
  complexity VARCHAR(50),
  file_url VARCHAR(500),     -- Original file path
  content_id INTEGER,         -- From "spaces/4/content/{id}/"
  s3_bucket VARCHAR(100),
  s3_key VARCHAR(500),
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  -- ... other fields
);
```

---

## Conclusion

**Current Status**: 
- ✅ Metadata structure understood
- ✅ 152 videos have local metadata
- ⚠️ Need database access for full metadata (7,228 videos)

**Action Required**: 
- Query PostgreSQL database to get complete video metadata
- Map database records to S3 hash filenames
- Create comprehensive inventory with all metadata

The metadata is there in your database - we just need to extract it and map it to the S3 files!

