# S3 Bucket Structure Overview - StayCurrentMD

## Executive Summary

Your S3 infrastructure supports the **StayCurrentMD** mobile application (https://github.com/GlobalCastMD/staycurrent-mobile) with a well-organized content delivery system. The buckets use a **hash-based content-addressable storage** pattern, which enables efficient deduplication and content integrity.

---

## Bucket Architecture

### 🏭 Production Bucket: `gcmd-production`
**Purpose**: Primary content storage for production app  
**Total Size**: ~1,839 GB  
**Total Files**: ~14,500+ objects

### 🧪 Testing Bucket: `gcmd-testing`
**Purpose**: Development and testing environment  
**Total Files**: ~3,500+ objects (mostly duplicates of production)

---

## Folder Structure

### Production Bucket (`gcmd-production`)

```
gcmd-production/
├── videos/                    # Main video content (3,997 videos, 677 GB)
│   ├── [hash].mp4            # Video files (hash-based naming)
│   ├── [hash].jpg/.png       # Thumbnails (4,315+ images)
│   ├── [hash].pdf            # Supporting documents (7 files)
│   └── [id].vtt/.websrt      # Subtitle files (4 files)
│
├── vimeo_videos/              # Vimeo-imported content (3,185 videos, 1,162 GB)
│   └── [hash].mp4            # Higher quality videos from Vimeo
│
├── conferences/               # Conference content (structure ready, empty)
│   └── media/                # Subfolder for conference media
│
└── Transcription/            # Transcription storage (folder ready, empty)
```

### Testing Bucket (`gcmd-testing`)

```
gcmd-testing/
├── videos/                    # Test videos (3,481 files)
│   └── Note: 3,434 are duplicates of production
│
├── dev-data/                  # Development data (4 files)
└── migration-test/            # Migration testing (1 file)
```

---

## Key Design Patterns

### 1. **Hash-Based Content-Addressable Storage**

**Pattern**: Files are named using cryptographic hashes (32-character hex strings)

**Example**:
- Video: `000a300e8f1e74ab4fec71506bea7096.mp4`
- Thumbnail: `000a300e8f1e74ab4fec71506bea7096.jpg`

**Benefits**:
- ✅ **Automatic Deduplication**: Same content = same hash = same file
- ✅ **Content Integrity**: Hash verifies file hasn't been corrupted
- ✅ **Unique Identification**: Hash serves as unique ID in database
- ✅ **Efficient Storage**: No duplicate files stored

### 2. **File Association Pattern**

Videos and their thumbnails share the same hash-based filename:
- Video: `[hash].mp4`
- Thumbnail: `[hash].jpg` (or `.png`)

This allows the app to:
1. Query database for video hash
2. Construct both video and thumbnail URLs using the same hash
3. Serve content efficiently

### 3. **Flat File Structure**

All files within each folder are stored at the root level (no subdirectories).

**Pros**:
- Simple to manage
- Fast access
- Easy to list/iterate

**Cons**:
- May become unwieldy as content grows
- No automatic organization by date/category

---

## Content Breakdown

### Videos
- **Production videos**: 3,997 files (677 GB)
  - Date range: March 2022 - February 2023
  - Average size: 173 MB
  - Format: MP4

- **Vimeo videos**: 3,185 files (1,162 GB)
  - Imported: July 19-20, 2023
  - Average size: 374 MB (higher quality)
  - Format: MP4

- **Total unique videos**: 7,182 (after deduplication: 7,228)

### Supporting Files
- **Thumbnails**: ~4,315+ images (JPG, PNG)
- **Subtitles**: 4 files (VTT, WebSRT formats)
- **PDFs**: 7 supporting documents

---

## How It Works with StayCurrentMD App

### Data Flow

```
┌─────────────────┐
│  Mobile App     │
│  (User Request) │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│   Database      │
│  (Video Metadata│
│   + Hash ID)    │
└────────┬────────┘
         │
         ▼
┌─────────────────┐
│  S3 Bucket      │
│  s3://gcmd-     │
│  production/    │
│  videos/[hash]  │
└─────────────────┘
```

### Typical Workflow

1. **User browses videos** in app
2. **App queries database** for video list
3. **Database returns** video metadata + hash IDs
4. **App constructs S3 URLs** using hash:
   - Video: `s3://gcmd-production/videos/{hash}.mp4`
   - Thumbnail: `s3://gcmd-production/videos/{hash}.jpg`
5. **Content served** via CloudFront CDN (likely) or direct S3 access

### Database Schema (Inferred)

The app likely has a database table like:

```sql
videos:
  - id (primary key)
  - hash (unique, maps to S3 filename)
  - title
  - description
  - specialty
  - procedure_type
  - complexity
  - created_at
  - s3_path (or constructed from hash)
```

---

## Storage Organization Insights

### Current State
- ✅ Well-organized by content type (videos, vimeo_videos, conferences)
- ✅ Hash-based naming prevents duplicates
- ✅ Thumbnails co-located with videos
- ✅ Separate testing environment

### Future-Ready Folders
- 📁 `conferences/` - Structure ready for conference content
- 📁 `Transcription/` - Ready for transcription results

### Observations
1. **Vimeo Migration**: Large batch import in July 2023 (3,185 videos)
2. **Transcription Work**: Folder exists but empty - work in progress
3. **Testing Environment**: Mostly duplicates of production (good for safe testing)
4. **No Metadata Files**: Metadata likely stored in database, not S3

---

## Recommendations

### Organization
1. ✅ Current flat structure works well for current scale
2. 📅 Consider date-based subfolders if content grows significantly
3. 📁 Use `conferences/` folder for upcoming conference content
4. 📝 Populate `Transcription/` folder as transcriptions complete

### Optimization
1. **CDN**: Likely using CloudFront for video delivery (recommended)
2. **Lifecycle Policies**: Consider archiving old/unused content
3. **Versioning**: Enable if you need to update video content
4. **CORS**: Ensure properly configured for mobile app access

### Data Management
1. **Deduplication**: Already handled by hash-based naming ✅
2. **Backup**: Consider cross-region replication for critical content
3. **Monitoring**: Track storage costs and access patterns

---

## File Naming Examples

### Video Files
```
000a300e8f1e74ab4fec71506bea7096.mp4  # Main video
00171459dd3bc4eb6cde3a6abe60b977.mp4  # Another video
```

### Associated Thumbnails
```
000a300e8f1e74ab4fec71506bea7096.jpg  # Thumbnail for first video
00171459dd3bc4eb6cde3a6abe60b977.png  # Thumbnail for second video
```

### Special Files
```
UpdateCourseGreyBG    # Branding/UI asset
GCMD_Text            # Text asset
Sarah, Melissa, etc. # Named content files
```

---

## Statistics Summary

| Metric | Production | Testing |
|--------|-----------|---------|
| **Total Videos** | 7,182 | 3,481 |
| **Unique Videos** | 7,182 | 47 |
| **Total Size** | 1,839 GB | 444 GB |
| **Thumbnails** | 4,315+ | - |
| **Date Range** | 2022-03 to 2023-07 | - |

---

## Integration Points

### StayCurrentMD Mobile App
- **Repository**: https://github.com/GlobalCastMD/staycurrent-mobile
- **Content Source**: `gcmd-production` bucket
- **Access Method**: Likely via CloudFront CDN or S3 presigned URLs
- **Metadata Source**: Database (not S3)

### Content Types Supported
- ✅ Medical procedure videos
- ✅ Conference recordings (folder ready)
- ✅ Thumbnails/previews
- ✅ Subtitles/captions
- ✅ Supporting PDFs

---

## Conclusion

Your S3 bucket structure is **well-designed** for a medical video content platform:

1. ✅ **Scalable**: Hash-based naming supports growth
2. ✅ **Efficient**: Automatic deduplication saves storage
3. ✅ **Organized**: Clear separation of content types
4. ✅ **Future-ready**: Folders prepared for conferences and transcriptions
5. ✅ **Safe**: Separate testing environment

The structure supports the StayCurrentMD app's need to serve medical educational content efficiently while maintaining data integrity and avoiding duplicates.

