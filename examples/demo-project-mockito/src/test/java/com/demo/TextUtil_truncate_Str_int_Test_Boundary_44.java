package com.demo;

import com.demo.TextUtil;
import org.junit.Assert;
import org.junit.Test;

public class TextUtil_truncate_Str_int_Test_Boundary_44 {


    @Test
    public void testTruncateWithNullString() {
        String s = null;
        int maxLength = 10;
        String result = TextUtil.truncate(s, maxLength);
        Assert.assertNull(result);
    }

}
