# Scrape Fundamaker Questions to MongoDB and S3

This plan outlines the approach to scrape all questions for all `s` (Subject) and `t` (Topic) combinations from the Fundamaker website, upload associated images to AWS S3, and insert the structured data into MongoDB.

## Schema Modifications

The updated MongoDB schema based on the actual data extracted:

```javascript
// Collection: questions
{
  _id: ObjectId,
  type: String,                         // required, enum: ['mcq', 'tita']
  
  text: String,                         // optional
  imageUrls: [String],                  // CHANGED: Array to support multiple images
  
  comprehensionId: ObjectId,            // optional, ref: Comprehension

  // MCQ only
  options: [
    {
      index: Number,                    // 0-based
      text: String,                     // optional
      imageUrls: [String],              // CHANGED: Array to support multiple images
    }
  ],
  correctOptionIndex: Number,           // required if type === 'mcq'

  // TITA only
  correctAnswer: String,                // CHANGED: String instead of Number to support fractions/text

  explanation: {
    text: String,                       // optional
    imageUrls: [String],                // CHANGED: Array
  },

  subject: String,                      // REQUIRED — e.g. "Quant", "VARC", "DILR"
  topic: String,                        // REQUIRED — e.g. "Permutation & Combination"
  tags: [String],                       // optional
  
  // NEW: Metadata
  year: Number,                         // optional - e.g., 2021
  shift: Number,                        // optional - e.g., 1, 2, or 3
  externalId: String,                   // optional - the question ID from the site to prevent duplicates

  createdAt: Date,
  updatedAt: Date,
}
```

Modifications:
- `difficulty` has been removed.
- `subject` and `topic` are now required fields.

## Approach

1. **Local HTML Support:** `scraper_db.py` will have support to scrape a local HTML file directly via CLI arguments (`--local`, `--subject`, `--topic`). It will parse it, upload any images to S3, and insert questions directly into MongoDB. This is useful for testing without hitting the live site.
2. **AWS S3 Integration:** The `boto3` library will be used to upload images to the S3 bucket using the credentials provided in `.env`. The URL stored in MongoDB will be the resulting S3 URL.
3. **MongoDB Integration:** The `pymongo` library will be used to upsert the parsed data, utilizing the `externalId` field to prevent duplication.
