package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_truncate_Str_int_Test_Normal_43 {


    @Test
    public void testTruncateWithRepresentativeInputs() {
        // maxLength equal to string length -> returns original string
        String result1 = TextUtil.truncate("test", 4);
        Assert.assertEquals("test", result1);

        // maxLength greater than string length -> returns original string
        String result2 = TextUtil.truncate("test", 10);
        Assert.assertEquals("test", result2);

        // maxLength 1 -> truncates and appends ellipsis
        String result3 = TextUtil.truncate("test", 1);
        Assert.assertEquals("t...", result3);

        // maxLength 0 -> empty prefix plus ellipsis
        String result4 = TextUtil.truncate("test", 0);
        Assert.assertEquals("...", result4);

        // empty string with maxLength 0 -> returns original empty string
        String result5 = TextUtil.truncate("", 0);
        Assert.assertEquals("", result5);

        // empty string with maxLength 1 -> returns original empty string
        String result6 = TextUtil.truncate("", 1);
        Assert.assertEquals("", result6);
    }

}
